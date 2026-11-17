"""Chrome options shared by local and Selenoid sessions."""

import os
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

from config import ROOT


def chrome_options() -> webdriver.ChromeOptions:
    options = webdriver.ChromeOptions()
    # Page Objects wait for the actual UI state after DOM readiness.
    options.page_load_strategy = "eager"
    options.add_argument("--window-size=1440,1000")
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    options.add_experimental_option(
        "prefs",
        {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        },
    )
    return options


def start_local_browser(profile: str, *, headed: bool) -> webdriver.Chrome:
    cache = ROOT / ".cache" / "selenium"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["SE_CACHE_PATH"] = str(cache)
    os.environ["SE_AVOID_STATS"] = "true"
    os.environ["SE_AVOID_BROWSER_DOWNLOAD"] = "true"
    options = chrome_options()
    if not headed:
        options.add_argument("--headless=new")
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument(f"--disk-cache-dir={profile}/cache")
    service = Service(env={**os.environ, "TMPDIR": str(Path(profile).parent)})
    return webdriver.Chrome(options=options, service=service)
