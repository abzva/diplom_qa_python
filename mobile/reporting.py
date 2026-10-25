"""Attach a completed BrowserStack session without publishing signed video URLs."""

import json

import allure
import requests

from reporting import attach_json, diagnostic, safe_url


def attach_completed_session(session_id, username, access_key, artifacts):
    record = {"session_id": session_id, "video_attached": False}

    def collect():
        response = requests.get(
            f"https://api-cloud.browserstack.com/app-automate/sessions/{session_id}.json",
            auth=(username, access_key), timeout=(15, 30), allow_redirects=False,
        )
        response.raise_for_status()
        session = response.json()["automation_session"]
        link = safe_url(session["browser_url"])
        record.update({"session_url": link, "status": session["status"],
                       "device": session.get("device"), "os_version": session.get("os_version"),
                       "app_version": session.get("app_details", {}).get("app_version")})
        allure.dynamic.link(link, name="BrowserStack: сессия и видео")

        def video():
            # Authentication is only for the API above. The signed storage URL
            # must never be attached or receive our BrowserStack Basic Auth.
            with requests.Session() as download:
                # Ignore .netrc, proxy and CA environment settings; default TLS verification stays on.
                download.trust_env = False
                with download.get(session["video_url"], timeout=(15, 30), stream=True) as stream:
                    record["video_http_status"] = stream.status_code
                    record["video_content_type"] = stream.headers.get("Content-Type")
                    stream.raise_for_status()
                    content = bytearray()
                    for chunk in stream.iter_content(64 * 1024):
                        content.extend(chunk)
                        record["video_bytes"] = len(content)
                        if len(content) > 50 * 1024 * 1024:
                            raise ValueError("Session video exceeds the 50 MiB diagnostic limit")
                    record["video_is_mp4"] = b"ftyp" in content[:32]
                    if not record["video_is_mp4"]:
                        raise ValueError("Video response is not an MP4 container")
                    path = artifacts / "video.mp4"
                    path.write_bytes(content)
                    allure.attach.file(str(path), name="Видео BrowserStack", attachment_type=allure.attachment_type.MP4)
                    record.update({"video_attached": True, "video_bytes": len(content)})

        diagnostic("BrowserStack video", video)

    diagnostic("BrowserStack session details", collect)
    (artifacts / "allure_session.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    attach_json("BrowserStack session and video availability", record)
