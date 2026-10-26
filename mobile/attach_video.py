"""Attach late BrowserStack video to a copy, preserving the original results."""

import argparse
import json
import shutil
from uuid import uuid4
from urllib.parse import urlsplit

from mobile.reporting import SESSION_ID_LABEL, attach_completed_session
from mobile.config import ROOT, MobileSettings
from reporting import register_cloud_credentials


def project_path(value):
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        raise ValueError("Use a path inside the project")
    return path


def find_session_result(source, session_id):
    matches = []
    for file in source.glob("*-result.json"):
        result = json.loads(file.read_text(encoding="utf-8"))
        ids = {label["value"] for label in result.get("labels", [])
               if label.get("name") == SESSION_ID_LABEL}
        # Compatibility with results created before the session ID label existed.
        linked_ids = set()
        for link in result.get("links", []):
            url = urlsplit(link.get("url", ""))
            parts = url.path.rstrip("/").split("/")
            if (url.hostname == "app-automate.browserstack.com"
                    and len(parts) >= 3 and parts[-2] == "sessions"):
                linked_ids.add(parts[-1])
        recorded_ids = ids | linked_ids
        if session_id in recorded_ids:
            if recorded_ids != {session_id}:
                raise ValueError("Conflicting BrowserStack session IDs in an original result")
            matches.append(file)
    if len(matches) != 1:
        raise ValueError("Expected exactly one original result linked to this session")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, help="Original allure-results directory")
    parser.add_argument("--output", required=True, help="New directory; must not already exist")
    parser.add_argument("--session-id", required=True)
    args = parser.parse_args()
    source, target = project_path(args.results), project_path(args.output)
    if target.exists():
        parser.error("Output already exists; choose a new directory to preserve diagnostics")
    if target.is_relative_to(source):
        parser.error("Output must be outside the original results directory")
    if not args.session_id.isalnum():
        parser.error("Expected an alphanumeric BrowserStack session ID")

    try:
        matched_result = find_session_result(source, args.session_id)
    except ValueError as error:
        parser.error(str(error))

    settings = MobileSettings.from_env_file()
    username, key = settings.username.get_secret_value(), settings.access_key.get_secret_value()
    register_cloud_credentials(username, key)
    target.mkdir(parents=True)
    artifacts = target / "late-video-diagnostics"
    artifacts.mkdir()
    attach_completed_session(args.session_id, username, key, artifacts)
    record = json.loads((artifacts / "allure_session.json").read_text())
    if not record["video_attached"]:
        parser.exit(1, "Video unavailable; diagnostics saved. Original results unchanged.\n")

    destination = target / "allure-results"
    shutil.copytree(source, destination)
    result_file = destination / matched_result.name
    result = json.loads(result_file.read_text())
    video_name = f"{uuid4()}-attachment.mp4"
    shutil.copy2(artifacts / "video.mp4", destination / video_name)
    note_name = f"{uuid4()}-attachment.json"
    record["note"] = "Video retrieved separately after the test. Original status, steps and duration unchanged."
    (destination / note_name).write_text(json.dumps(record, indent=2), encoding="utf-8")
    result.setdefault("attachments", []).extend([
        {"name": "Видео BrowserStack (получено после завершения теста)", "source": video_name, "type": "video/mp4"},
        {"name": "Позднее получение видео: диагностика", "source": note_name, "type": "application/json"},
    ])
    result_file.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    print(f"Video added to a copy: {destination.relative_to(ROOT)}; original results unchanged")


if __name__ == "__main__":
    main()
