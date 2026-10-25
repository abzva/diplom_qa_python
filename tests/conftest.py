"""Account lifecycle and a fresh local or Selenoid Chrome session per test."""

import json
import logging
import os
import re
import secrets
import tempfile
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from uuid import uuid4
from urllib.parse import urlsplit

import pytest
import allure
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.command import Command

from diplom_qa_python.api.accounts import read_account_response, verify_login
from diplom_qa_python.api.session import ApiSession
from config import ROOT, settings, SelenoidSettings
from models.account import CreateAccountRequest, Credentials
from selenoid import start_remote_browser, attach_session_record, finish_remote_reporting
from reporting import attach_driver_state, attach_json, diagnostic, register_secrets


logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", help="Show the local Chrome window")
    parser.addoption("--ui-mode", choices=("local", "selenoid"), default="local",
                     help="UI driver mode; remote mode must be selected explicitly")


@pytest.fixture
@allure.title("HTTP-сессия с безопасной диагностикой запросов и ответов")
def api_session():
    with ApiSession(base_url=settings.base_url) as session:
        yield session


@pytest.fixture
@allure.title("Уникальные данные своего аккаунта и обязательная очистка")
def account_data(request, api_session):
    unique_id = uuid4().hex
    user = CreateAccountRequest(
        name=f"Diploma {unique_id[:12]}",
        email=f"diploma_{unique_id}@example.test",
        password=secrets.token_urlsafe(24),
    )
    credentials = Credentials(email=user.email, password=user.password)
    register_secrets(user.password, user.email)

    def delete_user():
        # Registered before POST: also runs if setup/UI/assertions fail.
        # This separate copy always contains the original cleanup credentials.
        current = verify_login(api_session, credentials)
        if current.responseCode == 404:
            assert current.message == "User not found!", current
            logger.info("Cleanup confirmed for %s: account absent; DELETE skipped", credentials.email)
            return

        assert current.responseCode == 200, current
        assert current.message == "User exists!", current
        result = read_account_response(api_session.delete(
            "/api/deleteAccount",
            data=credentials.model_dump(),
            timeout=settings.api_timeout,
        ))
        assert result.responseCode == 200, result
        assert result.message == "Account deleted!", result

        missing = verify_login(api_session, credentials)
        assert missing.responseCode == 404, missing
        assert missing.message == "User not found!", missing
        logger.info("Cleanup confirmed for %s: account deleted and absence verified", credentials.email)

    def cleanup():
        with allure.step("Подтвердить отсутствие своего аккаунта; при необходимости удалить через API"):
            delete_user()

    request.addfinalizer(cleanup)
    logger.info("Generated own account data for %s; cleanup registered", credentials.email)
    return user


@pytest.fixture
@allure.title("Создать собственный аккаунт через API")
def test_user(account_data, api_session):
    result = read_account_response(api_session.post(
        "/api/createAccount",
        data=account_data.model_dump(),
        timeout=settings.api_timeout,
    ))
    assert result.responseCode == 201, result
    assert result.message == "User created!", result
    return account_data


@pytest.fixture
@allure.title("Новая сессия Chrome; диагностика и закрытие в teardown")
def browser(request):
    cache = ROOT / ".cache" / "selenium"
    temporary = ROOT / ".tmp" / "chrome"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    artifacts = ROOT / ".artifacts" / "ui" / f"{stamp}_{request.node.name}"
    for directory in (cache, temporary, artifacts):
        directory.mkdir(parents=True, exist_ok=True)

    remote = None
    record = None
    with ExitStack() as stack:
        if request.config.getoption("--ui-mode") == "selenoid":
            remote = SelenoidSettings.from_env_file()
            driver, video_name = start_remote_browser(remote)
            # Save these before quit: Selenium can clear session_id on shutdown.
            record = {"session_id": driver.session_id, "video_name": video_name,
                      "stage": "created", "quit_completed": False, "video_status": "pending"}
        else:
            # Selenium Manager and Chrome keep their test data in this repository.
            os.environ["SE_CACHE_PATH"] = str(cache)
            os.environ["SE_AVOID_STATS"] = "true"
            os.environ["SE_AVOID_BROWSER_DOWNLOAD"] = "true"
            service_environment = {**os.environ, "TMPDIR": str(temporary)}
            profile = stack.enter_context(tempfile.TemporaryDirectory(prefix="profile-", dir=temporary))
            options = webdriver.ChromeOptions()
            # Wait for DOM readiness; page objects wait for the actual UI state.
            options.page_load_strategy = "eager"
            if not request.config.getoption("--headed"):
                options.add_argument("--headless=new")
            options.add_argument("--window-size=1440,1000")
            options.add_argument(f"--user-data-dir={profile}")
            options.add_argument(f"--disk-cache-dir={profile}/cache")
            options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
            options.add_experimental_option("prefs", {
                "download.default_directory": str(artifacts / "downloads"),
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
            })
            driver = webdriver.Chrome(options=options, service=Service(env=service_environment))
        try:
            if record is not None:
                diagnostic("Selenoid initial metadata", lambda: attach_session_record(record, artifacts))
            driver.set_page_load_timeout(45)
            logger.info("Chrome version: %s", driver.capabilities["browserVersion"])
            yield driver
        finally:
            try:
                attach_driver_state(driver, artifacts)
                observations = driver.execute_script("""
                    return {
                        url: location.origin + location.pathname,
                        ready_state: document.readyState,
                        iframe_count: document.querySelectorAll('iframe').length,
                        advertising_frame_count: document.querySelectorAll(
                            'iframe[id*="google_ads"], iframe[id*="aswift"], iframe[src*="doubleclick"]'
                        ).length
                    };
                """)
                # Remote lacks ChromiumDriver.get_log(); both support this command.
                console = driver.execute(Command.GET_LOG, {"type": "browser"})["value"]
                observations["console_levels"] = dict(Counter(
                    entry["level"] for entry in console
                ))
                # Keep only hosts/error codes, never URL queries or credentials.
                observations["network_errors"] = [
                    {
                        "hosts": sorted({urlsplit(url).hostname for url in
                            re.findall(r"https?://[^\s]+", entry["message"])}),
                        "codes": re.findall(r"net::ERR_[A-Z_]+", entry["message"]),
                        "http_statuses": re.findall(r"status of (\d{3})", entry["message"]),
                        "source": entry["source"],
                    }
                    for entry in console if entry["level"] == "SEVERE"
                ]
                (artifacts / "browser_observation.json").write_text(
                    json.dumps(observations, indent=2), encoding="utf-8"
                )
                diagnostic("browser logs", lambda: attach_json("Browser logs (hosts/codes only)", observations))
                logger.info("Browser observation: %s", observations)
            except Exception as error:
                logger.warning("Could not save browser diagnostics: %s", type(error).__name__)
            finally:
                try:
                    driver.quit()
                    if record is not None:
                        record["quit_completed"] = True
                finally:
                    if record is not None:
                        record["stage"] = "finished"
                        # Reporting cannot hide a quit exception already propagating.
                        finish_remote_reporting(remote, record, artifacts)
