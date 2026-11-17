"""Account lifecycle and a fresh local or Selenoid Chrome session per test."""

import logging
import secrets
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack
from datetime import UTC, datetime
from uuid import uuid4

import allure
import pytest
from selenium.webdriver.remote.webdriver import WebDriver

from browser import start_local_browser
from config import ROOT, SelenoidSettings, settings
from diplom_qa_python.api.accounts import cleanup_account, read_account_response
from diplom_qa_python.api.session import ApiSession
from models.account import CreateAccountRequest, Credentials
from pages.cart_page import CartPage
from pages.catalog_page import CatalogPage
from pages.login_page import LoginPage
from pages.product_page import ProductPage
from reporting import attach_browser_logs, attach_driver_state, diagnostic, register_secrets
from selenoid import (
    SelenoidRecord,
    attach_session_record,
    finish_remote_reporting,
    start_remote_browser,
)

logger = logging.getLogger(__name__)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--headed", action="store_true", help="Show the local Chrome window")
    parser.addoption(
        "--ui-mode",
        choices=("local", "selenoid"),
        default="local",
        help="UI driver mode; remote mode must be selected explicitly",
    )


@pytest.fixture
@allure.title("HTTP-сессия с безопасной диагностикой запросов и ответов")
def api_session() -> Iterator[ApiSession]:
    with ApiSession(base_url=settings.base_url) as session:
        yield session


@pytest.fixture
@allure.title("Уникальные данные своего аккаунта и обязательная очистка")
def account_data(request: pytest.FixtureRequest, api_session: ApiSession) -> CreateAccountRequest:
    unique_id = uuid4().hex
    user = CreateAccountRequest(
        name=f"Diploma {unique_id[:12]}",
        email=f"diploma_{unique_id}@example.test",
        password=secrets.token_urlsafe(24),
    )
    credentials = Credentials(email=user.email, password=user.password)
    register_secrets(user.password, user.email)

    def cleanup() -> None:
        with allure.step(
            "Подтвердить отсутствие своего аккаунта; при необходимости удалить через API"
        ):
            cleanup_account(api_session, credentials)

    # Registered before POST; the copy retains the original cleanup credentials.
    request.addfinalizer(cleanup)  # noqa: PT021 - register cleanup before account creation can fail.
    logger.info("Generated own account data for %s; cleanup registered", credentials.email)
    return user


@pytest.fixture
@allure.title("Создать собственный аккаунт через API")
def test_user(account_data: CreateAccountRequest, api_session: ApiSession) -> CreateAccountRequest:
    result = read_account_response(
        api_session.post(
            "/api/createAccount",
            data=account_data.model_dump(),
            timeout=settings.api_timeout,
        )
    )
    assert result.responseCode == 201, result
    assert result.message == "User created!", result
    return account_data


@pytest.fixture
@allure.title("Новая сессия Chrome; диагностика и закрытие в teardown")
def browser(request: pytest.FixtureRequest) -> Iterator[WebDriver]:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    artifacts = ROOT / ".artifacts" / "ui" / f"{stamp}_{request.node.name}"
    artifacts.mkdir(parents=True, exist_ok=True)

    remote: SelenoidSettings | None = None
    record: SelenoidRecord | None = None
    with ExitStack() as stack:
        if request.config.getoption("--ui-mode") == "selenoid":
            remote = SelenoidSettings.from_env_file()
            driver, video_name = start_remote_browser(remote)
        else:
            temporary = ROOT / ".tmp" / "chrome"
            temporary.mkdir(parents=True, exist_ok=True)
            profile = stack.enter_context(
                tempfile.TemporaryDirectory(prefix="profile-", dir=temporary)
            )
            driver = start_local_browser(profile, headed=request.config.getoption("--headed"))
        try:
            if remote is not None:
                # Save before quit: Selenium can clear session_id on shutdown.
                record = {
                    "session_id": driver.session_id,
                    "video_name": video_name,
                    "stage": "created",
                    "quit_completed": False,
                    "video_status": "pending",
                }
                diagnostic(
                    "Selenoid initial metadata", lambda: attach_session_record(record, artifacts)
                )
            driver.set_page_load_timeout(45)
            logger.info("Chrome version: %s", driver.capabilities["browserVersion"])
            yield driver
        finally:
            try:
                diagnostic("browser state", lambda: attach_driver_state(driver, artifacts))
                diagnostic("browser logs", lambda: attach_browser_logs(driver, artifacts))
            finally:
                try:
                    driver.quit()
                    if record is not None:
                        record["quit_completed"] = True
                finally:
                    if record is not None and remote is not None:
                        record["stage"] = "finished"
                        # Reporting cannot hide a quit exception already propagating.
                        finish_remote_reporting(remote, record, artifacts)


@pytest.fixture
def catalog_page(browser: WebDriver) -> CatalogPage:
    return CatalogPage(browser)


@pytest.fixture
def product_page(browser: WebDriver) -> ProductPage:
    return ProductPage(browser)


@pytest.fixture
def cart_page(browser: WebDriver) -> CartPage:
    return CartPage(browser)


@pytest.fixture
def login_page(browser: WebDriver) -> LoginPage:
    return LoginPage(browser)
