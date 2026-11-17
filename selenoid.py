"""Remote Chrome creation and bounded collection of its completed session video."""

import json
import logging
from pathlib import Path
from time import monotonic, sleep
from typing import Literal, NotRequired, TypedDict
from uuid import uuid4

import allure
import requests
from pydantic import SecretStr
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.remote.webdriver import WebDriver
from urllib3.exceptions import HTTPError

from browser import chrome_options
from config import SelenoidSettings
from reporting import attach_json, diagnostic, register_cloud_credentials
from ui_diagnostics import collect_driver_log

logger = logging.getLogger(__name__)
VIDEO_WAIT_SECONDS = 30
VIDEO_POLL_SECONDS = 1
MAX_VIDEO_BYTES = 50 * 1024 * 1024


class SelenoidRecord(TypedDict):
    """The existing JSON record; optional fields appear during video collection."""

    session_id: str | None
    video_name: str
    stage: Literal["created", "finished"]
    quit_completed: bool
    video_status: Literal["pending", "unavailable", "attached"]
    video_attempts: NotRequired[int]
    video_http_status: NotRequired[int | None]
    video_bytes: NotRequired[int]
    video_error: NotRequired[str]
    driver_log_name: NotRequired[str]


def auth_pair(username: SecretStr | None, password: SecretStr | None) -> tuple[str, str] | None:
    if username is None:
        return None
    assert password is not None, "Selenoid settings must contain both credentials"
    pair = username.get_secret_value(), password.get_secret_value()
    register_cloud_credentials(*pair)
    return pair


def start_remote_browser(
    settings: SelenoidSettings, *, diagnostics: bool = False
) -> tuple[WebDriver, str]:
    video_name = f"{uuid4().hex}.mp4"
    options = chrome_options(diagnostics=diagnostics)
    options.browser_version = settings.browser_version
    selenoid_options: dict[str, object] = {
        "enableVideo": True,
        "videoName": video_name,
        "screenResolution": "1440x1000x24",
    }
    if diagnostics:
        selenoid_options.update(enableLog=True, logName=video_name.removesuffix(".mp4") + ".log")
    options.set_capability("selenoid:options", selenoid_options)
    credentials = auth_pair(settings.username, settings.password)
    connection = ClientConfig(
        remote_server_addr=settings.webdriver_url,
        username=credentials[0] if credentials else None,
        password=credentials[1] if credentials else None,
        timeout=120,
        init_args_for_pool_manager={"init_args_for_pool_manager": {"retries": 0}},
    )
    try:
        driver = webdriver.Remote(
            command_executor=settings.webdriver_url, options=options, client_config=connection
        )
    except (WebDriverException, HTTPError, OSError) as error:
        # Do not expose remote error bodies that might echo authentication headers.
        raise RuntimeError(f"Selenoid session creation failed: {type(error).__name__}") from None
    return driver, video_name


def attach_session_record(record: SelenoidRecord, artifacts: Path) -> None:
    """Metadata deliberately excludes endpoints, credentials and capabilities."""
    (artifacts / "selenoid_session.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    attach_json(f"Selenoid session and video ({record['stage']})", record)


def download_video(settings: SelenoidSettings, record: SelenoidRecord) -> bytes:
    """Only a 404 means 'not ready yet'; no test or navigation retries.

    Deadline is checked between HTTP reads. A pending socket read can add up to
    5 seconds; scheduler/OS overhead is outside that bound.
    """
    deadline = monotonic() + VIDEO_WAIT_SECONDS
    credentials = auth_pair(settings.video_username, settings.video_password)
    url = settings.video_base_url + "/" + record["video_name"]
    content = bytearray()
    with requests.Session() as session:
        # No implicit .netrc credentials/proxy/auth selection for the video endpoint.
        session.trust_env = False
        session.auth = credentials

        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("Video readiness deadline exceeded")
            record["video_attempts"] += 1
            with session.get(
                url,
                timeout=(min(3, remaining / 2), min(5, remaining / 2)),
                stream=True,
                allow_redirects=False,
            ) as response:
                record["video_http_status"] = response.status_code
                if response.status_code == 200:
                    # read1 returns currently available data; do not wait for a
                    # whole large chunk from a slowly streaming server.
                    while True:
                        if monotonic() >= deadline:
                            raise TimeoutError("Video download deadline exceeded")
                        chunk = response.raw.read1(64 * 1024, decode_content=True)
                        if not chunk:
                            break
                        content.extend(chunk)
                        if len(content) > MAX_VIDEO_BYTES:
                            record["video_error"] = "video_exceeds_50_mib"
                            raise ValueError("Video size limit exceeded")
                    if len(content) < 12 or content[4:8] != b"ftyp":
                        record["video_error"] = "invalid_mp4"
                        raise ValueError("Expected an MP4 container")
                    return bytes(content)
                if response.status_code != 404:
                    record["video_error"] = f"http_{response.status_code}"
                    raise ValueError("Unexpected video HTTP status")

            # A completed session's recording can appear with a delay.
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("Video readiness deadline exceeded")
            sleep(min(VIDEO_POLL_SECONDS, remaining))


def collect_video(settings: SelenoidSettings, record: SelenoidRecord, artifacts: Path) -> None:
    """Download and attach only after a confirmed session shutdown."""
    record.update({"video_status": "unavailable", "video_attempts": 0, "video_http_status": None})
    if not record["quit_completed"]:
        record["video_error"] = "session_close_failed"
        logger.warning("Selenoid video unavailable: session_close_failed")
        return
    try:
        content = download_video(settings, record)
        path = artifacts / record["video_name"]
        path.write_bytes(content)
        allure.attach.file(
            str(path), name="Видео Selenoid", attachment_type=allure.attachment_type.MP4
        )
        record.update({"video_status": "attached", "video_bytes": len(content)})
    except TimeoutError:
        record["video_error"] = "readiness_deadline_exceeded"
    except (requests.RequestException, HTTPError, OSError, ValueError) as error:
        record.setdefault("video_error", type(error).__name__)
    if record["video_status"] != "attached":
        logger.warning("Selenoid video unavailable: %s", record["video_error"])


def finish_remote_reporting(
    settings: SelenoidSettings, record: SelenoidRecord, artifacts: Path
) -> None:
    # This runs after quit even on test failure. Attachment failures are warnings,
    # while a failure of driver.quit itself remains a pytest teardown error.
    if not diagnostic("Selenoid video", lambda: collect_video(settings, record, artifacts)):
        record.update({"video_status": "unavailable", "video_error": "collection_failed"})
    diagnostic("Selenoid session metadata", lambda: attach_session_record(record, artifacts))
    if "driver_log_name" in record:
        diagnostic(
            "Selenoid driver log",
            lambda: collect_driver_log(settings, record["driver_log_name"], artifacts),
        )
