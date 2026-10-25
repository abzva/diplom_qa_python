"""Small, shared Allure helpers: safe text and best-effort diagnostics."""

import base64
import json
import logging
import re
from urllib.parse import parse_qsl, quote, quote_plus, urlsplit, urlunsplit

import allure
import allure_commons
import attrs
import requests


logger = logging.getLogger(__name__)
REDACTED = "[REDACTED]"
_secrets = set()
SENSITIVE = re.compile(
    r"password|passwd|secret|token|authorization|cookie|api.?key|access.?key|"
    r"username|email|address|phone|mobile_number|firstname|lastname|birth|zipcode",
    re.I,
)


def register_secrets(*values):
    # Keep values only in memory; also cover URL/form and Basic Auth encodings.
    for value in values:
        if value:
            _secrets.update((value, quote(value, safe=""), quote_plus(value)))


def register_cloud_credentials(username, key):
    register_secrets(username, key, base64.b64encode(f"{username}:{key}".encode()).decode())


def safe_url(url):
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
    except ValueError:
        return "[URL REDACTED]"
    # Query values and fragments can carry signed credentials. Never retain them.
    query = "&".join(f"{quote(k)}=REDACTED" for k, _ in parse_qsl(parts.query))
    return urlunsplit((parts.scheme, host, parts.path, query, ""))


def safe_text(value):
    text = str(value)
    for secret in sorted(_secrets, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    text = re.sub(
        r'''(?i)(["']?(?:password|passwd|access_key|api_key|token|secret|authorization|cookie)["']?\s*[:=]\s*)(["'])(.*?)\2''',
        lambda m: m[1] + m[2] + REDACTED + m[2], text,
    )
    # Also cover unknown signed URLs in exception messages.
    text = re.sub(r'https?://[^\s<>"\']+', lambda m: safe_url(m.group()), text)
    return text


def safe_data(value):
    if isinstance(value, dict):
        return {k: REDACTED if SENSITIVE.search(str(k)) else safe_data(v)
                for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe_data(v) for v in value]
    return safe_text(value) if isinstance(value, str) else value


def attach_json(name, value):
    allure.attach(json.dumps(safe_data(value), ensure_ascii=False, indent=2),
                  name=name, attachment_type=allure.attachment_type.JSON)


def diagnostic(name, operation):
    """One failed attachment must not block another attachment or driver.quit()."""
    try:
        operation()
        return True
    except Exception as error:
        logger.warning("Diagnostics unavailable (%s): %s", name, type(error).__name__)
        return False


def attach_http_request(request):
    def collect():
        body = request.body
        if isinstance(body, bytes):
            body = body.decode("utf-8", errors="replace")
        if body:
            if "application/json" in request.headers.get("Content-Type", ""):
                body = json.loads(body)
            else:
                body = dict(parse_qsl(body, keep_blank_values=True))
            for key, value in body.items():
                if re.search(r"password|passwd|secret|token|api.?key|access.?key|email", key, re.I):
                    register_secrets(str(value))
        attach_json("API request", {
            "method": request.method, "url": safe_url(request.url),
            "content_type": request.headers.get("Content-Type"), "body": body,
        })
    diagnostic("API request", collect)


def attach_http_response(response, **kwargs):
    """Includes GET and fixture cleanup exchanges; response is not changed."""
    def collect():
        try:
            content = response.json()
        except ValueError:
            content = safe_text(response.text)
        attach_json("API response", {
            "method": response.request.method, "url": safe_url(response.url),
            "http_status": response.status_code,
            "content_type": response.headers.get("Content-Type"), "body": content,
        })
    diagnostic("API response", collect)
    return response


class ReportingSession(requests.Session):
    """Only instrumentation: ordinary requests semantics, no retries or API logic."""

    def send(self, request, **kwargs):
        attach_http_request(request)
        try:
            response = super().send(request, **kwargs)
        except requests.RequestException as error:
            diagnostic("API transport error", lambda: attach_json("API: ответ не получен", {
                "method": request.method, "url": safe_url(request.url),
                "http_status": None, "error_type": type(error).__name__,
            }))
            raise
        attach_http_response(response)
        return response


def safe_page_source(source):
    # Work on the saved text only, never mutate the live page. Scripts and form
    # values can contain tokens even if they are not among our known secrets.
    source = re.sub(r"<script\b[^>]*>.*?</script>", "<!-- script omitted -->", source,
                    flags=re.I | re.S)
    source = re.sub(r'\b(value|content)\s*=\s*(["\']).*?\2',
                    r'\1="[REDACTED]"', source, flags=re.I | re.S)
    return safe_text(source)


def attach_driver_state(driver, artifacts, *, mobile=False):
    def screenshot():
        path = artifacts / "screen.png"
        if not driver.save_screenshot(str(path)):
            raise RuntimeError("Driver did not save a screenshot")
        allure.attach.file(str(path), name="Экран перед закрытием сессии",
                           attachment_type=allure.attachment_type.PNG)

    def source():
        path = artifacts / ("page.xml" if mobile else "page.html")
        path.write_text(safe_page_source(driver.page_source), encoding="utf-8")
        allure.attach.file(str(path), name="Page source (без секретов)",
                           attachment_type=allure.attachment_type.XML if mobile else allure.attachment_type.HTML)

    diagnostic("screenshot", screenshot)
    diagnostic("page source", source)


class AllureSecretFilter:
    """Redact raw result JSON, including parameters, before Allure writes it.

    Allure's MASKED display mode alone still stores the original value.
    """

    def _clean(self, value):
        if attrs.has(type(value)):
            for field in attrs.fields(type(value)):
                current = getattr(value, field.name)
                if field.name == "value" and SENSITIVE.search(str(getattr(value, "name", ""))):
                    setattr(value, field.name, REDACTED)
                else:
                    setattr(value, field.name, self._clean(current))
            return value
        if isinstance(value, str):
            return safe_text(value)
        if isinstance(value, list):
            return [self._clean(v) for v in value]
        if isinstance(value, dict):
            return safe_data(value)
        return value

    @allure_commons.hookimpl(tryfirst=True)
    def report_result(self, result):
        self._clean(result)

    @allure_commons.hookimpl(tryfirst=True)
    def report_container(self, container):
        self._clean(container)
