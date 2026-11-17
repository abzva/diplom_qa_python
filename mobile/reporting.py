"""Attach a completed BrowserStack session without publishing signed video URLs."""

import json
from pathlib import Path
from urllib.parse import urlsplit

import allure
import requests
from urllib3.exceptions import HTTPError

from mobile.browserstack import get_session
from mobile.video import download_video
from reporting import attach_json, diagnostic, safe_url

SESSION_ID_LABEL = "browserstack_session_id"


def save_session_metadata(metadata: dict, artifacts: Path) -> None:
    # Independent operations: an unwritable file must not prevent an Allure record.
    diagnostic(
        "Mobile session metadata file",
        lambda: (artifacts / "session.json").write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        ),
    )
    diagnostic(
        "Mobile session metadata attachment",
        lambda: attach_json(
            "Mobile session metadata",
            metadata,
        ),
    )


def attach_video(url: str, artifacts: Path, record: dict) -> None:
    path = artifacts / "video.mp4"
    try:
        download_video(url, path, record)
    except (requests.RequestException, HTTPError, OSError, ValueError) as error:
        # Exception messages can contain signed storage URLs; keep only the class.
        record["video_error_type"] = type(error).__name__
        raise
    record["video_stage"] = "attach"
    allure.attach.file(
        str(path), name="Видео BrowserStack", attachment_type=allure.attachment_type.MP4
    )
    record["video_attached"] = True
    record["video_stage"] = "attached"


def attach_session_details(
    session_id: str, username: str, access_key: str, artifacts: Path, record: dict
) -> None:
    session = get_session(session_id, username, access_key)
    link = safe_url(session["browser_url"])
    parsed = urlsplit(link)
    if parsed.hostname != "app-automate.browserstack.com" or not parsed.path.rstrip("/").endswith(
        f"/sessions/{session_id}"
    ):
        raise ValueError("BrowserStack returned a link to a different session")
    record.update(
        {
            "session_url": link,
            "status": session["status"],
            "device": session.get("device"),
            "os_version": session.get("os_version"),
            "app_version": session.get("app_details", {}).get("app_version"),
        }
    )
    allure.dynamic.link(link, name="BrowserStack: сессия и видео")
    diagnostic("BrowserStack video", lambda: attach_video(session["video_url"], artifacts, record))


def attach_completed_session(
    session_id: str, username: str, access_key: str, artifacts: Path
) -> None:
    record = {"session_id": session_id, "video_attached": False}
    diagnostic(
        "BrowserStack session details",
        lambda: attach_session_details(
            session_id,
            username,
            access_key,
            artifacts,
            record,
        ),
    )
    (artifacts / "allure_session.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    attach_json("BrowserStack session and video availability", record)
