import pytest
from contextlib import nullcontext as does_not_raise

from .common import basic_auth_headers
from mozapkpublisher.hag_api.error import (
    HagAuthenticationException,
    HagAppInfoException,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation,expected_app_id",
    (
        pytest.param(
            200,
            {"ret": {"code": 0, "msg": "success"}, "appids": [{"value": "12345678"}]},
            does_not_raise(),
            "12345678",
        ),
        pytest.param(
            200,
            {"ret": {"code": 0, "msg": "success"}, "appids": []},
            pytest.raises(HagAppInfoException, match="No app found"),
            None,
        ),
        pytest.param(
            401,
            {"ret": {"code": 401, "msg": "Invalid token"}},
            pytest.raises(HagAuthenticationException, match="Invalid token"),
            None,
        ),
    ),
)
async def test_get_app_id(hag, responses_mock, status, response, expectation, expected_app_id):
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName=org.mozilla.firefox",
        status=status,
        payload=response,
    )

    with expectation as exc:
        app_id = await hag.get_app_id("org.mozilla.firefox")

    if exc is None:
        assert app_id == expected_app_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {
                "ret": {"code": 0, "msg": "success"},
                "appInfo": {
                    "appName": "Firefox",
                    "packageName": "org.mozilla.firefox",
                    "status": "Released",
                },
            },
            does_not_raise(),
        ),
        pytest.param(
            401,
            {"ret": {"code": 401, "msg": "Invalid token"}},
            pytest.raises(HagAuthenticationException, match="Invalid token"),
        ),
    ),
)
async def test_get_app_info(hag, responses_mock, status, response, expectation):
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-info?appId=12345678",
        status=status,
        payload=response,
    )

    with expectation as exc:
        result = await hag.get_app_info("12345678")

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-info",
        method="GET",
        headers=basic_auth_headers(),
        params={"appId": "12345678"},
    )

    if exc is None:
        assert result["appInfo"]["appName"] == "Firefox"


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
async def test_update_app_file_info(hag, responses_mock, status, response, expectation):
    responses_mock.put(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info?appId=12345678",
        status=status,
        payload=response,
    )

    files = [{"fileName": "test.apk", "fileDestUrl": "https://example.com/test.apk"}]

    with expectation as exc:
        await hag.update_app_file_info("12345678", files)

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info",
        method="PUT",
        headers=basic_auth_headers(),
        params={"appId": "12345678"},
        json={"fileType": 5, "files": files},
    )
