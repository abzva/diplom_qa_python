"""BrowserStack capabilities and its session-management API."""

import requests
from appium.options.android import UiAutomator2Options

from mobile.config import MobileSettings

API_URL = "https://api-cloud.browserstack.com/app-automate/sessions"
API_TIMEOUT = (15, 30)


def session_options(settings: MobileSettings, name: str) -> UiAutomator2Options:
    return UiAutomator2Options().load_capabilities(
        {
            "platformName": "Android",
            "appium:automationName": "UiAutomator2",
            "appium:deviceName": settings.device_name,
            "appium:platformVersion": settings.platform_version,
            "appium:app": settings.app_url,
            "appium:language": "en",
            "appium:locale": "US",
            "appium:noReset": False,
            "bstack:options": {
                "projectName": "diplom_qa_python",
                "buildName": "Wikipedia Allure reporting",
                "sessionName": name,
                "video": True,
            },
        }
    )


def get_session(session_id: str, username: str, access_key: str) -> dict:
    with requests.get(
        f"{API_URL}/{session_id}.json",
        auth=(username, access_key),
        timeout=API_TIMEOUT,
        allow_redirects=False,
    ) as response:
        response.raise_for_status()
        return response.json()["automation_session"]


def set_session_status(
    session_id: str | None,
    username: str,
    access_key: str,
    *,
    status: str,
    reason: str,
) -> None:
    if not session_id:
        raise ValueError("Cannot update status without a session ID")
    with requests.put(
        f"{API_URL}/{session_id}.json",
        auth=(username, access_key),
        json={"status": status, "reason": reason},
        timeout=API_TIMEOUT,
        allow_redirects=False,
    ) as response:
        response.raise_for_status()
        if response.json()["automation_session"]["status"] != status:
            raise ValueError("BrowserStack did not confirm the requested test status")
