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


def read_json_response(response: requests.Response) -> dict:
    logger.info(
        "%s %s -> HTTP %s; Content-Type: %s",
        response.request.method, response.url, response.status_code,
        response.headers.get("Content-Type"),
    )
    assert response.status_code == 200, f"Unexpected HTTP status: {response.status_code}"
    # This API sends JSON with text/html; do not require application/json.
    body = read_json(response)
    assert isinstance(body, dict), "Expected a JSON object"
    logger.info("API body: responseCode=%s", body.get("responseCode"))
    return body


class ApiSession(ReportingSession):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url.rstrip("/")

    def request(self, method, url, **kwargs):
        # Keep API calls relative; a caller cannot silently select another host.
        if not url.startswith("/") or url.startswith("//"):
            raise ValueError("Use an API endpoint starting with a single slash")
        return super().request(method, self.base_url + url, **kwargs)
