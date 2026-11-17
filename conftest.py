"""Reporting only: no browser, cloud configuration or network on collection."""

from collections.abc import Generator

import allure_commons
import pytest
from pluggy import Result

from reporting import AllureSecretFilter, safe_text

SECRET_FILTER = pytest.StashKey[AllureSecretFilter]()


def pytest_configure(config: pytest.Config) -> None:
    secret_filter = AllureSecretFilter()
    config.stash[SECRET_FILTER] = secret_filter
    allure_commons.plugin_manager.register(secret_filter)


def pytest_unconfigure(config: pytest.Config) -> None:
    allure_commons.plugin_manager.unregister(config.stash[SECRET_FILTER])


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport() -> Generator[None, Result[pytest.TestReport]]:
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.longrepr = safe_text(report.longrepr)
    report.sections = [(name, safe_text(text)) for name, text in report.sections]
