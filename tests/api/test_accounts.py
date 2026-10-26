import allure

from diplom_qa_python.api.accounts import read_account_response, verify_login
from config import settings
from models.account import Credentials


pytestmark = [allure.parent_suite("API"), allure.epic("API"),
              allure.feature("Аккаунты"), allure.suite("Аккаунты")]


@allure.title("API-04: Создание аккаунта делает реквизиты действительными")
def test_create_account_accepts_original_credentials(account_data, api_session):
    """API-04: creation is the test action; the fixture only prepares data/cleanup."""
    with allure.step("Создать уникальный аккаунт через POST"):
        response = api_session.post(
            "/api/createAccount",
            data=account_data.model_dump(), timeout=settings.api_timeout,
        )
    with allure.step("Проверить HTTP 200, модель, бизнес-код 201 и сообщение"):
        created = read_account_response(response)
        assert created.responseCode == 201, created
        assert created.message == "User created!", created

    with allure.step("Подтвердить приём исходных реквизитов через verifyLogin"):
        credentials = Credentials(email=account_data.email, password=account_data.password)
        accepted = verify_login(api_session, credentials)
        assert accepted.responseCode == 200, accepted
        assert accepted.message == "User exists!", accepted


@allure.title("API-05: Удалённый аккаунт больше не может войти")
def test_delete_account_rejects_original_credentials(test_user, api_session):
    with allure.step("Удалить подготовленный аккаунт через DELETE"):
        credentials = Credentials(email=test_user.email, password=test_user.password)
        response = api_session.delete(
            "/api/deleteAccount",
            data=credentials.model_dump(), timeout=settings.api_timeout,
        )
    with allure.step("Проверить HTTP 200, модель и сообщение удаления"):
        deleted = read_account_response(response)
        assert deleted.responseCode == 200, deleted
        assert deleted.message == "Account deleted!", deleted

    with allure.step("Подтвердить отказ для исходных реквизитов"):
        missing = verify_login(api_session, credentials)
        assert missing.responseCode == 404, missing
        assert missing.message == "User not found!", missing


@allure.title("API-06: Неверный пароль отклонён, исходный продолжает работать")
def test_wrong_password_does_not_change_existing_account(test_user, api_session):
    with allure.step("Подготовить отличный пароль, сохранив исходные реквизиты"):
        original = Credentials(email=test_user.email, password=test_user.password)
        # Appending a suffix guarantees a different password without changing the original.
        incorrect = Credentials(email=original.email, password=original.password + "_wrong")

    with allure.step("Проверить HTTP 200, модель и отказ при неверном пароле"):
        rejected = verify_login(api_session, incorrect)
        assert rejected.responseCode == 404, rejected
        assert rejected.message == "User not found!", rejected

    with allure.step("Подтвердить приём исходного пароля"):
        accepted = verify_login(api_session, original)
        assert accepted.responseCode == 200, accepted
        assert accepted.message == "User exists!", accepted
