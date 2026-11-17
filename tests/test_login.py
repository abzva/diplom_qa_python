import secrets
from uuid import uuid4

import allure

from models.account import CreateAccountRequest, Credentials
from pages.login_page import LoginPage

pytestmark = [
    allure.parent_suite("UI"),
    allure.epic("UI"),
    allure.feature("Авторизация"),
    allure.suite("Авторизация"),
]


@allure.title("UI-01: Вход пользователя, подготовленного через API")
def test_login_with_api_created_user(
    user_login_page: LoginPage,
    test_user: CreateAccountRequest,
) -> None:
    with allure.step("Открыть форму входа"):
        user_login_page.open()
    with allure.step("Войти с реквизитами созданного пользователя"):
        user_login_page.login(test_user)
    with allure.step("Проверить точное имя пользователя и Logout"):
        user_login_page.should_be_logged_in_as(test_user.name)


@allure.title("UI-02: Несуществующий пользователь не может войти")
def test_login_rejects_nonexistent_user(login_page: LoginPage) -> None:
    with allure.step("Подготовить уникальные реквизиты и открыть вход"):
        credentials = Credentials(
            email=f"nonexistent_{uuid4().hex}@example.test",
            password=secrets.token_urlsafe(24),
        )
        login_page.open()

    with allure.step("Отправить форму с неверными реквизитами"):
        login_page.login(credentials)

    with allure.step("Проверить ошибку, доступность формы и отсутствие авторизации"):
        login_page.should_reject_login()
