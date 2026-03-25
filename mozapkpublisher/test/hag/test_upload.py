import pytest
import tempfile
import unittest

from contextlib import nullcontext as does_not_raise
from .common import basic_auth_headers
from mozapkpublisher.hag_api.error import (
    HagAuthenticationException,
    HagUploadException,
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {
                "ret": {"code": 0, "msg": "success"},
                "uploadUrl": "https://grs-file.cloud.huawei.com/FileServer/uploadFile",
                "authCode": "test_auth_code_123",
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
async def test_get_upload_url(hag, responses_mock, status, response, expectation):
    responses_mock.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId=12345678&suffix=apk",
        status=status,
        payload=response,
    )

    with expectation as exc:
        result = await hag.get_upload_url("12345678", suffix="apk")

    responses_mock.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/upload-url",
        method="GET",
        headers=basic_auth_headers(),
        params={"appId": "12345678", "suffix": "apk"},
    )

    if exc is None:
        assert result["uploadUrl"] == "https://grs-file.cloud.huawei.com/FileServer/uploadFile"
        assert result["authCode"] == "test_auth_code_123"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status,response,expectation",
    (
        pytest.param(
            200,
            {
                "ret": {"code": 0, "msg": "success"},
                "result": {
                    "UploadFileRsp": {
                        "fileInfoList": [
                            {
                                "fileDestUrl": "https://appdl-1.dbankcdn.com/dl/apk/test.apk",
                                "size": 10,
                            }
                        ]
                    }
                },
            },
            does_not_raise(),
        ),
        pytest.param(
            200,
            {
                "ret": {"code": 0, "msg": "success"},
                "result": {"UploadFileRsp": {"fileInfoList": []}},
            },
            pytest.raises(HagUploadException, match="no file info returned"),
        ),
        pytest.param(
            401,
            {"ret": {"code": 401, "msg": "Invalid token"}},
            pytest.raises(HagAuthenticationException, match="Invalid token"),
        ),
    ),
)
async def test_upload_file(hag, responses_mock, status, response, expectation):
    upload_url = "https://grs-file.cloud.huawei.com/FileServer/uploadFile"
    responses_mock.post(
        upload_url,
        status=status,
        payload=response,
    )

    with tempfile.NamedTemporaryFile("w", suffix=".apk") as tmp, expectation as exc:
        tmp.write("1" * 10)
        tmp.flush()
        result = await hag.upload_file(upload_url, "test_auth_code", tmp.name)

    responses_mock.assert_called_with(
        url=upload_url,
        method="POST",
        headers=basic_auth_headers(),
        data=unittest.mock.ANY,
    )

    if exc is None:
        assert result["fileDestUrl"] == "https://appdl-1.dbankcdn.com/dl/apk/test.apk"
