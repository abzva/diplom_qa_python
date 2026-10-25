import allure

import secrets
from uuid import uuid4

from models.account import Credentials
from pages.login_page import LoginPage


pytestmark = [allure.parent_suite("UI"), allure.epic("UI"),
              allure.feature("Авторизация"), allure.suite("Авторизация")]


@allure.title("UI-01: Вход пользователя, подготовленного через API")
def test_login_with_api_created_user(browser, test_user):
    with allure.step("Открыть форму входа"):
        page = LoginPage(browser)
        page.open()
    with allure.step("Войти с реквизитами созданного пользователя"):
        page.login(test_user)
    with allure.step("Проверить точное имя пользователя и Logout"):
        page.should_be_logged_in_as(test_user.name)


@allure.title("UI-02: Несуществующий пользователь не может войти")
def test_login_rejects_nonexistent_user(browser):
    with allure.step("Подготовить уникальные реквизиты и открыть вход"):
        credentials = Credentials(
            email=f"nonexistent_{uuid4().hex}@example.test",
            password=secrets.token_urlsafe(24),
        )
        page = LoginPage(browser)
        page.open()

    with allure.step("Отправить форму с неверными реквизитами"):
        page.login(credentials)

    with allure.step("Проверить ошибку, доступность формы и отсутствие авторизации"):
        page.should_reject_login()
