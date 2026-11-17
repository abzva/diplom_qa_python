"""Opt-in UI diagnostics: retain timings and events, never raw protocol payloads."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

import requests
from selenium.webdriver.remote.command import Command
from selenium.webdriver.remote.webdriver import WebDriver

from config import SelenoidSettings
from reporting import attach_json

LOAD_EVENTS = {
    "Network.requestWillBeSent",
    "Network.responseReceived",
    "Network.loadingFinished",
    "Network.loadingFailed",
    "Page.frameStartedLoading",
    "Page.frameStoppedLoading",
    "Page.frameNavigated",
    "Page.domContentEventFired",
    "Page.loadEventFired",
}
MAX_DRIVER_LOG_BYTES = 1024 * 1024
DRIVER_COMMANDS = {
    "InitSession",
    "Quit",
    "Navigate",
    "ClickElement",
    "FindElement",
    "FindElements",
    "GetUrl",
    "GetTitle",
    "GetSource",
    "GetLog",
    "GetElementText",
    "GetElementAttribute",
    "IsElementDisplayed",
    "IsElementEnabled",
    "ExecuteScript",
    "ExecuteAsyncScript",
    "Screenshot",
    "SetTimeouts",
    "GetTimeouts",
    "GetWindowRect",
    "SetWindowRect",
}


def location_summary(url: str) -> dict[str, str]:
    """Keep a host and only known public shop routes; discard all other URL data."""
    parts = urlsplit(url)
    summary = {"host": parts.hostname or ""}
    if parts.hostname == "automationexercise.com" and re.fullmatch(
        r"/|/products|/view_cart|/login|/product_details/\d+", parts.path
    ):
        summary["path"] = parts.path
    return summary


def loading_events(entries: list[dict]) -> list[dict]:
    events = []
    for entry in entries:
        message = json.loads(entry["message"])["message"]
        method = message["method"]
        if method not in LOAD_EVENTS:
            continue
        params = message["params"]
        event: dict[str, object] = {"event": method}
        if isinstance(entry.get("timestamp"), (int, float)):
            event["log_timestamp_ms"] = entry["timestamp"]
        for key in ("timestamp", "wallTime", "encodedDataLength"):
            if isinstance(params.get(key), (int, float)):
                event[key] = params[key]
        for key in ("requestId", "frameId", "loaderId"):
            if isinstance(params.get(key), str):
                event[key] = hashlib.sha256(params[key].encode()).hexdigest()[:16]
        for key in ("request", "response", "redirectResponse", "frame"):
            data = params.get(key, {})
            detail: dict[str, object] = {}
            if isinstance(data.get("url"), str):
                detail.update(location_summary(data["url"]))
            if isinstance(data.get("status"), (int, float)):
                detail["status"] = data["status"]
            if data.get("method") in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
                detail["method"] = data["method"]
            if key == "frame" and data:
                detail["main_frame"] = not bool(data.get("parentId"))
                for frame_key in ("id", "parentId", "loaderId"):
                    if isinstance(data.get(frame_key), str):
                        detail[frame_key] = hashlib.sha256(data[frame_key].encode()).hexdigest()[
                            :16
                        ]
            if detail:
                event[key] = detail
        error = params.get("errorText", "")
        if re.fullmatch(r"net::ERR_[A-Z_]+", error):
            event["error"] = error
        if isinstance(params.get("canceled"), bool):
            event["canceled"] = params["canceled"]
        events.append(event)
    return events


def save_diagnostic(name: str, filename: str, data: dict, artifacts: Path) -> None:
    (artifacts / filename).write_text(json.dumps(data, indent=2), encoding="utf-8")
    attach_json(name, data)


def attach_loading_trace(driver: WebDriver, artifacts: Path) -> None:
    record: dict[str, object] = {"collected_at": datetime.now(UTC).isoformat()}
    try:
        entries = driver.execute(Command.GET_LOG, {"type": "performance"})["value"]
        record.update(status="collected", events=loading_events(entries))
        strategy = driver.capabilities.get("pageLoadStrategy")
        if strategy in {"none", "eager", "normal"}:
            record["page_load_strategy"] = strategy
        version = driver.capabilities.get("browserVersion", "")
        if re.fullmatch(r"[0-9.]+", version):
            record["browser_version"] = version
    except Exception as error:
        record.update(status="unavailable", error_type=type(error).__name__)
        raise
    finally:
        save_diagnostic("Chrome loading trace (filtered)", "loading_trace.json", record, artifacts)


def driver_events(text: str) -> list[dict[str, object]]:
    """Drop command arguments, response bodies and arbitrary error messages."""
    events = []
    for line in text.splitlines():
        match = re.search(
            r"\[([0-9.]+)\]\[(INFO|DEBUG|WARNING|SEVERE)\]: "
            r"\[[0-9a-f]+\] (COMMAND|RESPONSE) ([A-Za-z]+)",
            line,
        )
        if match and match[4] in DRIVER_COMMANDS:
            event: dict[str, object] = dict(
                zip(("timestamp", "level", "phase", "command"), match.groups(), strict=True)
            )
            event["error"] = " ERROR " in line
            event["renderer_timeout"] = "Timed out receiving message from renderer" in line
            events.append(event)
        elif "Timed out receiving message from renderer" in line:
            stamp = re.search(r"\[([0-9.]+)\]", line)
            events.append(
                {"event": "renderer_timeout", "timestamp": stamp[1] if stamp else "unknown"}
            )
    return events


def collect_driver_log(settings: SelenoidSettings, name: str, artifacts: Path) -> None:
    """One bounded read after quit; a missing log is reported, never retried."""
    parts = urlsplit(settings.webdriver_url)
    url = f"{parts.scheme}://{parts.netloc}/logs/{name}"
    record: dict[str, object] = {"status": "unavailable", "log_name": name}
    try:
        with requests.Session() as session:
            session.trust_env = False
            if settings.username is not None and settings.password is not None:
                session.auth = (
                    settings.username.get_secret_value(),
                    settings.password.get_secret_value(),
                )
            with session.get(url, timeout=(3, 5), stream=True, allow_redirects=False) as response:
                record["http_status"] = response.status_code
                if response.status_code == 200:
                    content = response.raw.read(MAX_DRIVER_LOG_BYTES + 1, decode_content=True)
                    if len(content) > MAX_DRIVER_LOG_BYTES:
                        record["reason"] = "driver_log_exceeds_1_mib"
                    elif "html" in response.headers.get("Content-Type", "").lower():
                        record["reason"] = "unexpected_html"
                    else:
                        events = driver_events(content.decode("utf-8", errors="replace"))
                        record.update(
                            status="collected" if events else "no_command_events",
                            source_bytes=len(content),
                            events=events,
                        )
    except Exception as error:
        record["error_type"] = type(error).__name__
        raise
    finally:
        save_diagnostic("Selenoid driver log (filtered)", "driver_log.json", record, artifacts)
