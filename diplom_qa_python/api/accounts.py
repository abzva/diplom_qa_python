"""Only the response parsing and login check reused by account scenarios."""

import logging

import requests

from config import settings
from diplom_qa_python.api.session import ApiSession, read_json
from models.account import AccountResponse, Credentials


logger = logging.getLogger(__name__)


def read_account_response(response: requests.Response) -> AccountResponse:
    logger.info("%s %s -> HTTP %s", response.request.method, response.url, response.status_code)
    assert response.status_code == 200, f"Unexpected HTTP status: {response.status_code}"
    result = AccountResponse.model_validate(read_json(response))
    logger.info("Account API body: responseCode=%s", result.responseCode)
    return result


def verify_login(session: ApiSession, credentials: Credentials) -> AccountResponse:
    return read_account_response(session.post(
        "/api/verifyLogin",
        data=credentials.model_dump(),
        timeout=settings.api_timeout,
    ))
