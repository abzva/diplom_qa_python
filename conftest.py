"""Reporting only: no browser, cloud configuration or network on collection."""

import allure_commons
import pytest

from reporting import AllureSecretFilter, safe_text


def pytest_configure(config):
    config.diploma_secret_filter = AllureSecretFilter()
    allure_commons.plugin_manager.register(config.diploma_secret_filter)


def pytest_unconfigure(config):
    allure_commons.plugin_manager.unregister(config.diploma_secret_filter)


@pytest.hookimpl(hookwrapper=True, trylast=True)
def pytest_runtest_makereport():
    outcome = yield
    report = outcome.get_result()
    if report.failed:
        report.longrepr = safe_text(report.longrepr)
    report.sections = [(name, safe_text(text)) for name, text in report.sections]
