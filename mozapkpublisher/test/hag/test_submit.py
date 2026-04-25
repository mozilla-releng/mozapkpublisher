import pytest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.hag_api.error import (
    HagAuthenticationException,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {"ret": {"code": 0, "msg": "success"}},
            does_not_raise(),
        ),
        pytest.param(
            401,
            {"ret": {"code": 401, "msg": "Invalid token"}},
            pytest.raises(HagAuthenticationException, match="Invalid token"),
        ),
    ),
)
async def test_submit_app(hag, responses_mock, status, response, expectation):
    responses_mock.post(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=12345678",
        status=status,
        payload=response,
    )

    with expectation as exc:
        result = await hag.submit_app("12345678")

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
        method="POST",
        headers=basic_auth_headers(),
        params={"appId": "12345678"},
        json={"releaseType": 1},
    )

    if exc is None:
        assert result["ret"]["code"] == 0


@pytest.mark.asyncio
async def test_submit_app_with_rollout(hag, responses_mock):
    responses_mock.post(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=12345678",
        status=200,
        payload={"ret": {"code": 0, "msg": "success"}},
    )

    result = await hag.submit_app("12345678", release_type=3, phased_percent=25)

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
        method="POST",
        headers=basic_auth_headers(),
        params={"appId": "12345678"},
        json={"releaseType": 3, "phasedReleasePercent": 25},
    )

    assert result["ret"]["code"] == 0
