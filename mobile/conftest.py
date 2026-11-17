"""A fresh remote session; diagnostics never prevent driver.quit()."""

import logging
from collections.abc import Generator, Iterator
from datetime import UTC, datetime

import allure
import pytest
import requests
from appium import webdriver
from appium.webdriver.client_config import AppiumClientConfig
from pluggy import Result
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import HTTPError

from mobile.browserstack import session_options, set_session_status
from mobile.config import ROOT, MobileSettings
from mobile.pages.search_page import SearchPage
from mobile.reporting import SESSION_ID_LABEL, attach_completed_session, save_session_metadata
from reporting import attach_driver_state, diagnostic, register_cloud_credentials, safe_text

logger = logging.getLogger(__name__)
CALL_PASSED = pytest.StashKey[bool]()
INITIAL_SEARCH_EMPTY = pytest.StashKey[bool]()


@pytest.fixture
@allure.title("Проверить локальные настройки BrowserStack")
def mobile_settings() -> MobileSettings:
    return MobileSettings.from_env_file()


@pytest.fixture
@allure.title("Открыть поиск и проверить сброс состояния Wikipedia")
def search_page(
    request: pytest.FixtureRequest,
    mobile_driver: webdriver.Remote,
    mobile_settings: MobileSettings,
) -> SearchPage:
    page = SearchPage(mobile_driver, timeout=mobile_settings.timeout)
    with allure.step("Проверить пустой запрос, историю и отсутствие результатов в новой сессии"):
        page.open_fresh_search()
    request.node.stash[INITIAL_SEARCH_EMPTY] = True
    return page


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item) -> Generator[None, Result[pytest.TestReport]]:
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.stash[CALL_PASSED] = report.passed


@pytest.fixture
@allure.title("Новая Android-сессия; диагностика, закрытие и статус BrowserStack")
def mobile_driver(
    request: pytest.FixtureRequest,
    mobile_settings: MobileSettings,
) -> Iterator[webdriver.Remote]:
    settings = mobile_settings
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    artifacts = ROOT / ".artifacts" / "mobile" / f"{stamp}_{request.node.name}"
    artifacts.mkdir(parents=True)
    metadata = {
        "device": settings.device_name,
        "os_version": settings.platform_version,
        "quit_completed": False,
    }
    username = settings.username.get_secret_value()
    access_key = settings.access_key.get_secret_value()
    register_cloud_credentials(username, access_key)

    options = session_options(settings, request.node.name)
    # Credentials are HTTP authentication, not part of the URL or capabilities.
    connection = AppiumClientConfig(
        remote_server_addr="https://hub-cloud.browserstack.com/wd/hub",
        username=username,
        password=access_key,
        timeout=120,
        init_args_for_pool_manager={"init_args_for_pool_manager": {"retries": 0}},
    )
    try:
        driver = webdriver.Remote(options=options, client_config=connection)
    except (WebDriverException, HTTPError, OSError) as error:
        metadata["setup_error"] = f"{type(error).__name__}: {safe_text(error)}"
        save_session_metadata(metadata, artifacts)
        raise RuntimeError(metadata["setup_error"]) from None

    session_id: str | None = None
    try:
        session_id = driver.session_id
        assert isinstance(session_id, str), "Appium returned no session ID"
        assert session_id, "Appium returned an empty session ID"
        metadata["session_id"] = session_id
        allure.dynamic.label(SESSION_ID_LABEL, session_id)
        save_session_metadata(metadata, artifacts)
        logger.info("BrowserStack session created; artifacts: %s", artifacts.relative_to(ROOT))
        yield driver
    finally:
        metadata["test_passed"] = request.node.stash.get(CALL_PASSED, False)
        metadata["initial_search_empty"] = request.node.stash.get(INITIAL_SEARCH_EMPTY, False)
        teardown_errors: list[str] = []
        try:
            diagnostic(
                "Mobile driver state", lambda: attach_driver_state(driver, artifacts, mobile=True)
            )
        finally:
            try:
                driver.quit()
                metadata["quit_completed"] = True
                logger.info("BrowserStack session closed")
            except (WebDriverException, HTTPError, OSError) as error:
                quit_error = f"{type(error).__name__}: {safe_text(error)}"
                metadata["quit_error"] = quit_error
                teardown_errors.append(quit_error)
            finally:
                # Even an unexpected quit error must preserve metadata and a failed status.
                status = (
                    "passed" if metadata["test_passed"] and metadata["quit_completed"] else "failed"
                )
                try:
                    set_session_status(
                        session_id,
                        username,
                        access_key,
                        status=status,
                        reason=f"{request.node.name}: {status}",
                    )
                    metadata["browserstack_status"] = status
                except (requests.RequestException, KeyError, TypeError, ValueError) as error:
                    status_error = f"{type(error).__name__}: {safe_text(error)}"
                    metadata["status_update_error"] = status_error
                    teardown_errors.append(status_error)
                finally:
                    save_session_metadata(metadata, artifacts)
                if metadata["quit_completed"] and isinstance(session_id, str) and session_id:
                    diagnostic(
                        "completed BrowserStack session",
                        lambda: attach_completed_session(
                            session_id,
                            username,
                            access_key,
                            artifacts,
                        ),
                    )
        if teardown_errors:
            raise RuntimeError("; ".join(teardown_errors)) from None
