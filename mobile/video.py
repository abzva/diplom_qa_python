"""Bounded download from video storage, without BrowserStack credentials."""

from pathlib import Path
from time import monotonic

import requests

MAX_VIDEO_BYTES = 50 * 1024 * 1024
VIDEO_DOWNLOAD_SECONDS = 60


def download_video(url: str, destination: Path, record: dict) -> None:
    deadline = monotonic() + VIDEO_DOWNLOAD_SECONDS
    record["video_stage"] = "request"
    with requests.Session() as download:
        # Storage receives neither API auth nor implicit .netrc/proxy credentials.
        download.trust_env = False
        with download.get(url, timeout=(15, 30), stream=True) as response:
            record["video_http_status"] = response.status_code
            record["video_content_type"] = response.headers.get("Content-Type")
            response.raise_for_status()
            record["video_stage"] = "read"
            content = bytearray()
            while True:
                if monotonic() >= deadline:
                    record["video_error"] = "download_deadline_exceeded"
                    raise TimeoutError("Video download deadline exceeded")
                chunk = response.raw.read1(64 * 1024, decode_content=True)
                if not chunk:
                    break
                content.extend(chunk)
                record["video_bytes"] = len(content)
                if len(content) > MAX_VIDEO_BYTES:
                    record["video_error"] = "video_exceeds_50_mib"
                    raise ValueError("Session video exceeds the 50 MiB diagnostic limit")
            record["video_stage"] = "validate"
            record["video_is_mp4"] = b"ftyp" in content[:32]
            if not record["video_is_mp4"]:
                record["video_error"] = "invalid_mp4"
                raise ValueError("Video response is not an MP4 container")
            record["video_stage"] = "save"
            destination.write_bytes(content)
            record["video_stage"] = "saved"
