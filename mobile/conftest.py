"""A fresh remote session; diagnostics never prevent driver.quit()."""

import json
import logging
from datetime import datetime, timezone

import pytest
import requests
import allure
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.client_config import AppiumClientConfig

from mobile.config import ROOT, MobileSettings
from mobile.pages.search_page import SearchPage
from mobile.reporting import attach_completed_session
from reporting import attach_driver_state, attach_json, diagnostic, register_cloud_credentials, safe_text


logger = logging.getLogger(__name__)


@pytest.fixture
@allure.title("Проверить локальные настройки BrowserStack")
def mobile_settings():
    return MobileSettings.from_env_file()


@pytest.fixture
@allure.title("Открыть поиск и проверить сброс состояния Wikipedia")
def search_page(request, mobile_driver, mobile_settings):
    page = SearchPage(mobile_driver, timeout=mobile_settings.timeout)
    with allure.step("Проверить пустой запрос, историю и отсутствие результатов в новой сессии"):
        page.open_fresh_search()
    request.node.mobile_initial_search_empty = True
    return page


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call":
        item.mobile_call_passed = report.passed


@pytest.fixture
@allure.title("Новая Android-сессия; диагностика, закрытие и статус BrowserStack")
def mobile_driver(request, mobile_settings):
    settings = mobile_settings
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    artifacts = ROOT / ".artifacts" / "mobile" / f"{stamp}_{request.node.name}"
    artifacts.mkdir(parents=True)
    metadata = {"device": settings.device_name, "os_version": settings.platform_version,
                "quit_completed": False}
    username = settings.username.get_secret_value()
    access_key = settings.access_key.get_secret_value()
    register_cloud_credentials(username, access_key)

    def safe_error(error):
        return f"{type(error).__name__}: {safe_text(error)}"

    def save_metadata():
        saved = diagnostic("Mobile session metadata", lambda: (artifacts / "session.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8",
        ))
        if not saved:
            metadata.setdefault("diagnostic_errors", []).append("session_metadata_write_failed")
            diagnostic("Mobile metadata fallback", lambda: attach_json(
                "Mobile session metadata: file unavailable", metadata,
            ))

    options = UiAutomator2Options().load_capabilities({
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
            "sessionName": request.node.name,
            "video": True,
        },
    })
    # Credentials are HTTP authentication, not part of the URL or capabilities.
    connection = AppiumClientConfig(
        remote_server_addr="https://hub-cloud.browserstack.com/wd/hub",
        username=username, password=access_key, timeout=120,
        init_args_for_pool_manager={"init_args_for_pool_manager": {"retries": 0}},
    )
    try:
        driver = webdriver.Remote(options=options, client_config=connection)
    except Exception as error:
        metadata["setup_error"] = safe_error(error)
        save_metadata()
        raise RuntimeError(metadata["setup_error"]) from None

    try:
        metadata["session_id"] = driver.session_id
        save_metadata()
        logger.info("BrowserStack session created; artifacts: %s", artifacts.relative_to(ROOT))
        yield driver
    finally:
        metadata["test_passed"] = getattr(request.node, "mobile_call_passed", False)
        metadata["initial_search_empty"] = getattr(request.node, "mobile_initial_search_empty", False)
        teardown_errors = []
        try:
            try:
                attach_driver_state(driver, artifacts, mobile=True)
            except Exception as error:
                metadata["diagnostics_error"] = safe_error(error)
                logger.warning("Could not save Mobile diagnostics: %s", type(error).__name__)
        finally:
            try:
                driver.quit()
                metadata["quit_completed"] = True
                logger.info("BrowserStack session closed")
            except Exception as error:
                metadata["quit_error"] = safe_error(error)
                teardown_errors.append(metadata["quit_error"])
            finally:
                save_metadata()
        # Mark the completed session, taking quit failure into account.
        status = "passed" if metadata["test_passed"] and not teardown_errors else "failed"
        try:
            response = requests.put(
                f"https://api-cloud.browserstack.com/app-automate/sessions/{metadata['session_id']}.json",
                auth=(username, access_key), json={"status": status, "reason": f"{request.node.name}: {status}"},
                timeout=(15, 30), allow_redirects=False,
            )
            response.raise_for_status()
            if response.json()["automation_session"]["status"] != status:
                raise ValueError("BrowserStack did not confirm the requested test status")
            metadata["browserstack_status"] = status
        except Exception as error:
            metadata["status_update_error"] = safe_error(error)
            teardown_errors.append(metadata["status_update_error"])
        finally:
            save_metadata()
        diagnostic("completed BrowserStack session", lambda: attach_completed_session(
            metadata["session_id"], username, access_key, artifacts,
        ))
        if teardown_errors:
            raise RuntimeError("; ".join(teardown_errors)) from None
