from aiohttp import ClientResponseError

import pytest
from contextlib import nullcontext as does_not_raise

from mozapkpublisher.hag_api.auth import create_access_token
from mozapkpublisher.hag_api.error import (
    HagAuthenticationException,
    HagAuthorizationException,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {"access_token": "abc123token", "expires_in": 3600, "token_type": "Bearer"},
            does_not_raise(),
        ),
        pytest.param(
            200,
            {"ret": {"code": 401, "msg": "Invalid client_id"}, "access_token": None},
            pytest.raises(HagAuthenticationException, match="Invalid client_id"),
        ),
        pytest.param(
            401,
            {"ret": {"code": 401, "msg": "Unauthorized"}},
            pytest.raises(HagAuthenticationException, match="Unauthorized"),
        ),
        pytest.param(
            403,
            {"ret": {"code": 403, "msg": "Forbidden"}},
            pytest.raises(HagAuthorizationException, match="Forbidden"),
        ),
        pytest.param(
            500,
            {"message": "Internal server error"},
            pytest.raises(ClientResponseError, match="Internal server error"),
        ),
    ),
)
async def test_create_token(status, response, expectation, responses_mock):
    responses_mock.post(
        "https://connect-api.cloud.huawei.com/api/oauth2/v1/token",
        status=status,
        payload=response,
    )
    with expectation as exc:
        token = await create_access_token("test_client_id", "test_client_secret")

    if exc is None:
        assert token == "abc123token"
