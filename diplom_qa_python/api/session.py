"""API endpoints relative to the base URL selected by the pytest fixture."""

import logging
from urllib.parse import urlsplit

import requests

from reporting import ReportingSession, safe_text


logger = logging.getLogger(__name__)


def response_summary(response: requests.Response) -> str:
    """Describe the format without copying arbitrary HTML, cookies or query values."""
    body = response.text.lower()
    if "<html" in body or "<!doctype html" in body:
        description = "HTML"
        if "one moment, please..." in body and "please wait while your request is being verified" in body:
            description = "HTML verification page (One moment, please...)"
    else:
        description = "non-JSON body"
    endpoint = safe_text(urlsplit(response.url).path)
    content_type = safe_text(response.headers.get("Content-Type", "<missing>"))[:120]
    return f"{endpoint}: HTTP {response.status_code}; Content-Type={content_type!r}; {description}"


def read_json(response: requests.Response):
    try:
        return response.json()
    except requests.exceptions.JSONDecodeError as error:
        summary = response_summary(response)
        error.add_note(summary)
        logger.error("Expected JSON: %s", summary)
        raise


class ApiSession(ReportingSession):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")

    def request(self, method, url, **kwargs):
        # Keep API calls relative; a caller cannot silently select another host.
        if not url.startswith("/") or url.startswith("//"):
            raise ValueError("Use an API endpoint starting with a single slash")
        return super().request(method, self.base_url + url, **kwargs)
