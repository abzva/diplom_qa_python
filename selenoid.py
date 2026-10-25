"""Remote Chrome creation and bounded collection of its completed session video."""

import json
import logging
from time import monotonic
from uuid import uuid4

import allure
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.client_config import ClientConfig
from selenium.webdriver.support.ui import WebDriverWait

from reporting import attach_json, diagnostic, register_cloud_credentials


logger = logging.getLogger(__name__)
VIDEO_WAIT_SECONDS = 30
VIDEO_POLL_SECONDS = 1
MAX_VIDEO_BYTES = 50 * 1024 * 1024


def auth_pair(username, password):
    if username is None:
        return None
    pair = username.get_secret_value(), password.get_secret_value()
    register_cloud_credentials(*pair)
    return pair


def start_remote_browser(settings):
    video_name = f"{uuid4().hex}.mp4"
    options = webdriver.ChromeOptions()
    options.page_load_strategy = "eager"
    options.browser_version = settings.browser_version
    options.add_argument("--window-size=1440,1000")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    options.add_experimental_option("prefs", {
        "credentials_enable_service": False, "profile.password_manager_enabled": False,
    })
    options.set_capability("selenoid:options", {
        "enableVideo": True, "videoName": video_name,
        "screenResolution": "1440x1000x24",
    })
    credentials = auth_pair(settings.username, settings.password)
    connection = ClientConfig(
        remote_server_addr=settings.webdriver_url,
        username=credentials[0] if credentials else None,
        password=credentials[1] if credentials else None,
        timeout=120,
        init_args_for_pool_manager={"init_args_for_pool_manager": {"retries": 0}},
    )
    try:
        driver = webdriver.Remote(command_executor=settings.webdriver_url,
                                  options=options, client_config=connection)
    except Exception as error:
        # Do not expose remote error bodies that might echo authentication headers.
        raise RuntimeError(f"Selenoid session creation failed: {type(error).__name__}") from None
    return driver, video_name


def attach_session_record(record, artifacts):
    """Metadata deliberately excludes endpoints, credentials and capabilities."""
    (artifacts / "selenoid_session.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    attach_json(f"Selenoid session and video ({record['stage']})", record)


def collect_video(settings, record, artifacts):
    """Only a 404 means 'not ready yet'; no test or navigation retries.

    Deadline is checked between HTTP reads. A pending socket read can add up to
    5 seconds; scheduler/OS overhead is outside that bound.
    """
    record.update(video_status="unavailable", video_attempts=0, video_http_status=None)
    if not record["quit_completed"]:
        record["video_error"] = "session_close_failed"
        logger.warning("Selenoid video unavailable: session_close_failed")
        return
    deadline = monotonic() + VIDEO_WAIT_SECONDS
    credentials = auth_pair(settings.video_username, settings.video_password)
    url = settings.video_base_url + "/" + record["video_name"]
    content = bytearray()
    try:
        with requests.Session() as session:
            # No implicit .netrc credentials/proxy/auth selection for the video endpoint.
            session.trust_env = False
            session.auth = credentials

            def ready(_):
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutException()
                record["video_attempts"] += 1
                with session.get(url, timeout=(min(3, remaining / 2), min(5, remaining / 2)),
                                 stream=True, allow_redirects=False) as response:
                    record["video_http_status"] = response.status_code
                    if response.status_code == 404:
                        return False
                    if response.status_code != 200:
                        record["video_error"] = f"http_{response.status_code}"
                        raise ValueError("Unexpected video HTTP status")
                    # read1 returns currently available data; do not wait for a
                    # whole large chunk from a slowly streaming server.
                    while True:
                        if monotonic() >= deadline:
                            raise TimeoutException()
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
                    return True

            WebDriverWait(session, VIDEO_WAIT_SECONDS, poll_frequency=VIDEO_POLL_SECONDS).until(ready)
        path = artifacts / record["video_name"]
        path.write_bytes(content)
        allure.attach.file(str(path), name="Видео Selenoid", attachment_type=allure.attachment_type.MP4)
        record.update(video_status="attached", video_bytes=len(content))
    except TimeoutException:
        record["video_error"] = "readiness_deadline_exceeded"
    except Exception as error:
        record.setdefault("video_error", type(error).__name__)
    if record["video_status"] != "attached":
        logger.warning("Selenoid video unavailable: %s", record["video_error"])


def finish_remote_reporting(settings, record, artifacts):
    # This runs after quit even on test failure. Attachment failures are warnings,
    # while a failure of driver.quit itself remains a pytest teardown error.
    if not diagnostic("Selenoid video", lambda: collect_video(settings, record, artifacts)):
        record.update(video_status="unavailable", video_error="collection_failed")
    diagnostic("Selenoid session metadata", lambda: attach_session_record(record, artifacts))
