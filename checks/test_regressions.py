"""Offline regressions for reporting, search, cleanup and late Mobile video."""

import importlib.util
import json
import socket
import sys
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock

import allure_commons
import pytest
import requests
from allure_commons.logger import AllureFileLogger
from allure_commons.model2 import TestResult as AllureResult
from allure_pytest.listener import AllureListener

import config
import mobile.config
import mobile.conftest as mobile_fixtures
import mobile.attach_video as late_video
import reporting
from diplom_qa_python.api.accounts import cleanup_account
from diplom_qa_python.api.session import read_json, read_json_response
from mobile.reporting import SESSION_ID_LABEL
from models.account import Credentials
from models.product import ProductSnapshot, select_search_products
from pages.catalog_page import CatalogPage


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, config.ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


api_tests = load_module("catalog_scenarios", "tests/api/test_products.py")
account_fixtures = load_module("account_fixtures", "tests/conftest.py")


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Offline checks must not use the network or read .env")

    monkeypatch.setattr(requests.Session, "request", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(config, "dotenv_values", forbidden)
    monkeypatch.setattr(mobile.config, "dotenv_values", forbidden)


@pytest.fixture
def allure_capture(tmp_path, request):
    """Use real Allure serialization, independently of --alluredir."""
    listener = AllureListener(request.config)
    directory = tmp_path / "allure"
    writer = AllureFileLogger(directory)
    allure_commons.plugin_manager.register(listener)
    allure_commons.plugin_manager.register(writer)
    reporter = listener.allure_logger
    reporter.schedule_test("synthetic", AllureResult(uuid="synthetic", name="Offline scenario"))
    try:
        yield reporter, directory
    finally:
        if reporter.get_test("synthetic") is not None:
            reporter.close_test("synthetic")
        allure_commons.plugin_manager.unregister(writer)
        allure_commons.plugin_manager.unregister(listener)


def response(body, *, method="GET", status=200):
    result = requests.Response()
    result.status_code = status
    result.url = "https://example.test/api/fixture"
    result.request = requests.Request(method, result.url).prepare()
    result.headers["Content-Type"] = "text/html; charset=utf-8"
    result._content = (body if isinstance(body, str) else json.dumps(body)).encode()
    return result


@pytest.mark.parametrize("status", [200, 503])
def test_non_json_attachment_omits_hidden_token_and_keeps_parse_error(allure_capture, status):
    _, directory = allure_capture
    token = "synthetic-hidden-value-2791"
    original = response(f'<html><input type="hidden" name="csrf" value="{token}"></html>', status=status)
    with pytest.raises(requests.exceptions.JSONDecodeError) as parsed:
        original.json()
    original.json = Mock(side_effect=parsed.value)

    assert reporting.attach_http_response(original) is original
    attachments = list(directory.glob("*-attachment.json"))
    assert len(attachments) == 1
    attached_text = attachments[0].read_text()
    assert token not in attached_text and "<input" not in attached_text
    payload = json.loads(attached_text)
    assert payload["http_status"] == status
    assert payload["content_type"] == "text/html; charset=utf-8"
    assert payload["body_format"] == "HTML; body omitted"
    assert "body" not in payload
    with pytest.raises(requests.exceptions.JSONDecodeError) as error:
        read_json(original)
    assert error.value is parsed.value
    assert "HTML" in error.value.__notes__[0]
    if status != 200:
        with pytest.raises(AssertionError, match="Unexpected HTTP status: 503"):
            read_json_response(original)


CATALOG = [
    {"id": 1, "name": "Blue Top", "price": "Rs. 100"},
    {"id": 2, "name": "Green Jeans", "price": "Rs. 200"},
    {"id": 3, "name": "Blue Top Long", "price": "Rs. 300"},
]


@pytest.mark.parametrize("result_ids", [(1,), (1, 3), (1, 2, 3)])
def test_api_search_rejects_unfiltered_catalog(result_ids):
    session = Mock()
    session.get.return_value = response({"responseCode": 200, "products": CATALOG})
    session.post.return_value = response({
        "responseCode": 200, "products": [p for p in CATALOG if p["id"] in result_ids],
    })
    if 2 in result_ids:
        with pytest.raises(AssertionError, match="Unrelated catalog product"):
            api_tests.test_search_existing_product(session)
    else:
        api_tests.test_search_existing_product(session)
    assert session.post.call_args.kwargs["data"] == {"search_product": "Blue Top"}


@pytest.mark.parametrize("result_ids", [(1,), (1, 3), (1, 2, 3)])
def test_ui_search_rejects_unfiltered_catalog(result_ids):
    products = [ProductSnapshot(p["id"], p["name"], Decimal("100")) for p in CATALOG]
    selected, unrelated = select_search_products(products)
    page = CatalogPage(Mock())
    page.wait = Mock()
    page.products = Mock(return_value=[p for p in products if p.product_id in result_ids])
    if 2 in result_ids:
        with pytest.raises(AssertionError, match="Unrelated catalog product"):
            page.should_show_search_result(selected, unrelated)
    else:
        page.should_show_search_result(selected, unrelated)


@pytest.mark.parametrize("names", [[], [""], ["Blue Top"], ["Blue Top", "Blue Top Long"]])
def test_search_without_control_cannot_pass(names):
    with pytest.raises(AssertionError, match="no name query with an unrelated control"):
        select_search_products([SimpleNamespace(name=name) for name in names])


OWN = Credentials(email="diploma_synthetic@example.test", password="synthetic-password")
PRESENT = {"responseCode": 200, "user": {"id": 42, "email": OWN.email}}
ABSENT = {"responseCode": 404, "message": "Account not found with this email, try another email!"}
LOGIN_REJECTED = {"responseCode": 404, "message": "User not found!"}
DELETED = {"responseCode": 200, "message": "Account deleted!"}


def account_session(lookups, deletion=DELETED):
    session = Mock()
    session.get.side_effect = [item if isinstance(item, Exception) else response(item) for item in lookups]
    session.delete.side_effect = (
        deletion if isinstance(deletion, Exception) else lambda *a, **kw: response(deletion, method="DELETE")
    )
    # Login rejection must never be used to infer absence.
    session.post.return_value = response(LOGIN_REJECTED, method="POST")
    return session


def test_existing_account_with_rejected_credentials_still_gets_delete():
    session = account_session([PRESENT, PRESENT], deletion=LOGIN_REJECTED)
    with pytest.raises(ExceptionGroup, match="очистка не подтверждена") as error:
        cleanup_account(session, OWN)
    assert len(error.value.exceptions) == 2
    session.delete.assert_called_once_with(
        "/api/deleteAccount", data=OWN.model_dump(), timeout=config.settings.api_timeout,
    )
    session.post.assert_not_called()


def test_successful_deletion_is_confirmed_by_email_without_password():
    session = account_session([PRESENT, ABSENT])
    cleanup_account(session, OWN)
    assert session.get.call_count == 2
    for call in session.get.call_args_list:
        assert call.args == ("/api/getUserDetailByEmail",)
        assert call.kwargs == {"params": {"email": OWN.email}, "timeout": config.settings.api_timeout}
    session.delete.assert_called_once()
    session.post.assert_not_called()


def test_already_absent_account_does_not_need_delete():
    session = account_session([ABSENT])
    cleanup_account(session, OWN)
    session.delete.assert_not_called()
    session.post.assert_not_called()


@pytest.mark.parametrize("bad_lookup", [
    requests.Timeout("synthetic lookup timeout"),
    {"responseCode": 500, "message": "Unavailable"},
    {"responseCode": 404, "message": "Authentication failed"},
    LOGIN_REJECTED,
    {"responseCode": 200},
    {"responseCode": 200, "user": {"id": 42, "email": "someone-else@example.test"}},
    "<html>Verification page</html>",
])
def test_failed_lookup_keeps_error_and_does_not_skip_delete(bad_lookup):
    session = account_session([bad_lookup, ABSENT])
    with pytest.raises(ExceptionGroup, match="очистка не подтверждена") as error:
        cleanup_account(session, OWN)
    session.delete.assert_called_once()
    if isinstance(bad_lookup, Exception):
        assert error.value.exceptions[0] is bad_lookup


@pytest.mark.parametrize("phase", ["delete", "confirmation"])
def test_cleanup_timeout_is_not_success(phase):
    timeout = requests.Timeout("synthetic cleanup timeout")
    session = account_session(
        [PRESENT, timeout if phase == "confirmation" else ABSENT],
        deletion=timeout if phase == "delete" else DELETED,
    )
    with pytest.raises(ExceptionGroup, match="очистка не подтверждена") as error:
        cleanup_account(session, OWN)
    assert timeout in error.value.exceptions


def test_creation_timeout_has_early_finalizer_with_original_credentials():
    finalizers = []
    session = Mock()
    user = account_fixtures.account_data.__wrapped__(SimpleNamespace(addfinalizer=finalizers.append), session)
    assert len(finalizers) == 1
    original_email, original_password = user.email, user.password
    timeout = requests.Timeout("synthetic creation timeout after server accepted account")
    session.post.side_effect = timeout
    with pytest.raises(requests.Timeout) as error:
        account_fixtures.test_user.__wrapped__(user, session)
    assert error.value is timeout
    user.password = "changed-after-creation"
    session.get.side_effect = [
        response({"responseCode": 200, "user": {"id": 42, "email": original_email}}), response(ABSENT),
    ]
    session.delete.return_value = response(DELETED, method="DELETE")
    finalizers[0]()
    assert session.delete.call_args.kwargs["data"] == {
        "email": original_email, "password": original_password,
    }


@pytest.mark.parametrize("legacy", [False, True])
def test_late_video_finds_new_and_legacy_result(tmp_path, legacy):
    data = ({"links": [{"url": "https://app-automate.browserstack.com/builds/build/sessions/session123"}]}
            if legacy else {"labels": [{"name": SESSION_ID_LABEL, "value": "session123"}]})
    file = tmp_path / "one-result.json"
    file.write_text(json.dumps(data))
    assert late_video.find_session_result(tmp_path, "session123") == file


@pytest.mark.parametrize("conflict", ["duplicate", "inconsistent", "missing"])
def test_late_video_rejects_ambiguous_or_missing_session(tmp_path, conflict):
    data = {"labels": [{"name": SESSION_ID_LABEL, "value": "session123"}]}
    if conflict == "inconsistent":
        data["links"] = [{"url": "https://app-automate.browserstack.com/builds/b/sessions/different"}]
    if conflict != "missing":
        (tmp_path / "one-result.json").write_text(json.dumps(data))
    if conflict == "duplicate":
        (tmp_path / "two-result.json").write_text(json.dumps(data))
    with pytest.raises(ValueError):
        late_video.find_session_result(tmp_path, "session123")


def test_mobile_metadata_timeout_still_allows_late_video_recovery(tmp_path, monkeypatch, allure_capture):
    reporter, results = allure_capture
    settings = mobile.config.MobileSettings.model_validate({
        "BROWSERSTACK_USERNAME": "synthetic-user", "BROWSERSTACK_ACCESS_KEY": "synthetic-key",
        "BROWSERSTACK_APP_URL": "bs://synthetic", "BROWSERSTACK_DEVICE_NAME": "Synthetic device",
        "BROWSERSTACK_PLATFORM_VERSION": "13.0",
    })
    driver = Mock(session_id="session123")
    monkeypatch.setattr(mobile_fixtures, "ROOT", tmp_path)
    monkeypatch.setattr(mobile_fixtures.webdriver, "Remote", Mock(return_value=driver))
    monkeypatch.setattr(mobile_fixtures, "attach_driver_state", Mock())
    monkeypatch.setattr(requests, "put", Mock(return_value=response({"automation_session": {"status": "passed"}})))
    metadata_request = Mock(side_effect=requests.ReadTimeout("synthetic metadata timeout"))
    monkeypatch.setattr(requests, "get", metadata_request)
    node = SimpleNamespace(name="offline_mobile", mobile_call_passed=True, mobile_initial_search_empty=True)
    fixture = mobile_fixtures.mobile_driver.__wrapped__(SimpleNamespace(node=node), settings)
    assert next(fixture) is driver
    assert any(label.name == SESSION_ID_LABEL and label.value == "session123"
               for label in reporter.get_test("synthetic").labels)
    metadata_request.assert_not_called()
    with pytest.raises(StopIteration):
        next(fixture)
    driver.quit.assert_called_once()
    metadata_request.assert_called_once()
    reporter.close_test("synthetic")
    original = late_video.find_session_result(results, "session123")
    before = original.read_bytes()
    assert not json.loads(before).get("links")

    def available_video(session_id, username, key, artifacts):
        assert session_id == "session123"
        (artifacts / "allure_session.json").write_text(json.dumps({"session_id": session_id, "video_attached": True}))
        (artifacts / "video.mp4").write_bytes(b"synthetic offline video")

    monkeypatch.setattr(late_video, "ROOT", tmp_path)
    monkeypatch.setattr(late_video.MobileSettings, "from_env_file", lambda: settings)
    monkeypatch.setattr(late_video, "attach_completed_session", available_video)
    monkeypatch.setattr(sys, "argv", ["attach_video", "--results", "allure", "--output", "recovered",
                                     "--session-id", "session123"])
    late_video.main()
    assert original.read_bytes() == before
    recovered = json.loads((tmp_path / "recovered" / "allure-results" / original.name).read_text())
    assert recovered["labels"] == json.loads(before)["labels"]
    assert recovered["attachments"][-2]["type"] == "video/mp4"
    assert (tmp_path / "recovered" / "allure-results" / recovered["attachments"][-2]["source"]).read_bytes() == b"synthetic offline video"
