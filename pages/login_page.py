"""The login form and the authenticated header, without API setup logic."""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as conditions
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from models.account import Credentials
from reporting import register_secrets


logger = logging.getLogger(__name__)


class LoginPage:
    EMAIL = (By.CSS_SELECTOR, '[data-qa="login-email"]')
    PASSWORD = (By.CSS_SELECTOR, '[data-qa="login-password"]')
    SUBMIT = (By.CSS_SELECTOR, '[data-qa="login-button"]')
    ERROR = (By.CSS_SELECTOR, ".login-form form p")
    LOGGED_IN = (By.XPATH, "//header//a[contains(., 'Logged in as')]")
    LOGOUT = (By.CSS_SELECTOR, 'header a[href="/logout"]')

    def __init__(self, browser):
        self.browser = browser
        self.wait = WebDriverWait(browser, settings.ui_timeout)

    def open(self):
        logger.info("UI: opening the login form")
        self.browser.get(f"{settings.base_url}/login")
        self.wait.until(conditions.visibility_of_element_located(self.EMAIL))
        logger.info("UI: login form is visible")

    def login(self, credentials: Credentials):
        register_secrets(credentials.password, credentials.email)
        self.wait.until(conditions.element_to_be_clickable(self.EMAIL)).send_keys(
            credentials.email
        )
        self.wait.until(conditions.element_to_be_clickable(self.PASSWORD)).send_keys(
            credentials.password
        )
        self.wait.until(conditions.element_to_be_clickable(self.SUBMIT)).click()
        logger.info("UI: login form submitted")

    def should_reject_login(self):
        error = self.wait.until(conditions.visibility_of_element_located(self.ERROR))
        assert error.text == "Your email or password is incorrect!", error.text
        for locator in (self.EMAIL, self.PASSWORD, self.SUBMIT):
            self.wait.until(conditions.element_to_be_clickable(locator))
        for locator in (self.LOGGED_IN, self.LOGOUT):
            self.wait.until_not(
                conditions.presence_of_element_located(locator),
                message=f"Unexpected authenticated header element: {locator}",
            )
        logger.info("UI: login rejected; form remains available, user name and Logout are absent")

    def should_be_logged_in_as(self, name: str):
        header = self.wait.until(
            conditions.visibility_of_element_located(self.LOGGED_IN)
        )
        actual = " ".join(header.text.split())
        assert actual == f"Logged in as {name}", (
            f"Expected authenticated user {name!r}, got header {actual!r}"
        )
        self.wait.until(conditions.visibility_of_element_located(self.LOGOUT))
        logger.info("UI confirmed the expected user: %s", name)
