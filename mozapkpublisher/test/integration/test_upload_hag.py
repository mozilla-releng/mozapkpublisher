import os
import pytest
import unittest

from aioresponses import aioresponses
from mozapkpublisher.push_apk import push_apk
from mozapkpublisher.hag_api.error import HagAppInfoException
from ..hag.common import basic_auth_headers
import mozapkpublisher


UPLOAD_URL = "https://grs-file.cloud.huawei.com/FileServer/uploadFile"


def setup_default_hag_api(responses):
    # Auth token
    responses.post(
        "https://connect-api.cloud.huawei.com/api/oauth2/v1/token",
        status=200,
        payload={
            "access_token": "access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )

    # Get app ID
    responses.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName=org.mozilla.focus",
        status=200,
        payload={
            "ret": {"code": 0, "msg": "success"},
            "appids": [{"value": "12345678"}],
        },
    )

    # Get upload URL
    responses.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/upload-url?appId=12345678&suffix=apk",
        status=200,
        payload={
            "ret": {"code": 0, "msg": "success"},
            "uploadUrl": UPLOAD_URL,
            "authCode": "test_auth_code",
        },
    )

    # Upload file
    responses.post(
        UPLOAD_URL,
        status=200,
        payload={
            "ret": {"code": 0, "msg": "success"},
            "result": {
                "UploadFileRsp": {
                    "fileInfoList": [
                        {
                            "fileDestUrl": "https://appdl-1.dbankcdn.com/dl/apk/test.apk",
                            "size": 15,
                        }
                    ]
                }
            },
        },
    )

    # Update app file info
    responses.put(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info?appId=12345678",
        status=200,
        payload={"ret": {"code": 0, "msg": "success"}},
    )

    # Submit
    responses.post(
        "https://connect-api.cloud.huawei.com/api/publish/v2/app-submit?appId=12345678",
        status=200,
        payload={"ret": {"code": 0, "msg": "success"}},
    )


@pytest.fixture
def responses():
    with aioresponses() as responses:
        yield responses


def fake_apk_metadata(files, *args, **kwargs):
    ret = {}
    for file in files:
        ret[open(file, "rb")] = {
            "package_name": "org.mozilla.focus",
            "api_level": 21,
            "version_code": "390842050",
            "version_name": "137.1",
            "architecture": "armeabi-v7a",
            "locales": ("fr", "en"),
        }

    return ret


async def run_push_apk(monkeypatch, rollout_rate=None, submit=False):
    file = os.path.join(os.path.dirname(__file__), "../", "data", "blob")
    monkeypatch.setattr(
        mozapkpublisher.push_apk, "extract_and_check_apks_metadata", fake_apk_metadata
    )

    await push_apk(
        [file],
        None,
        ["org.mozilla.focus"],
        "release",
        store="huawei",
        rollout_percentage=rollout_rate,
        dry_run=False,
        contact_server=True,
        skip_check_ordered_version_codes=False,
        skip_check_multiple_locales=False,
        skip_check_same_locales=False,
        skip_checks_fennec=True,
        submit=submit,
        hag_client_id="test_client_id",
        hag_client_secret="test_client_secret",
    )


@pytest.mark.parametrize("rollout_rate", (25, None))
@pytest.mark.parametrize("submit", (True, False))
@pytest.mark.asyncio
async def test_update_ok(responses, monkeypatch, rollout_rate, submit):
    setup_default_hag_api(responses)
    await run_push_apk(monkeypatch, rollout_rate, submit)

    responses.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/appid-list",
        method="GET",
        headers=basic_auth_headers(),
        params={"packageName": "org.mozilla.focus"},
    )
    responses.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/upload-url",
        method="GET",
        headers=basic_auth_headers(),
        params={"appId": "12345678", "suffix": "apk"},
    )
    responses.assert_called_with(
        url=UPLOAD_URL,
        method="POST",
        headers=basic_auth_headers(),
        data=unittest.mock.ANY,
    )
    responses.assert_called_with(
        url="https://connect-api.cloud.huawei.com/api/publish/v2/app-file-info",
        method="PUT",
        headers=basic_auth_headers(),
        params={"appId": "12345678"},
        json={
            "fileType": 5,
            "files": [
                {
                    "fileName": "blob",
                    "fileDestUrl": "https://appdl-1.dbankcdn.com/dl/apk/test.apk",
                }
            ],
        },
    )

    if submit:
        if rollout_rate is not None:
            responses.assert_called_with(
                url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
                method="POST",
                headers=basic_auth_headers(),
                params={"appId": "12345678"},
                json={"releaseType": 3, "phasedReleasePercent": 25},
            )
        else:
            responses.assert_called_with(
                url="https://connect-api.cloud.huawei.com/api/publish/v2/app-submit",
                method="POST",
                headers=basic_auth_headers(),
                params={"appId": "12345678"},
                json={"releaseType": 1},
            )


@pytest.mark.asyncio
async def test_update_with_app_not_found(responses, monkeypatch):
    # Auth token
    responses.post(
        "https://connect-api.cloud.huawei.com/api/oauth2/v1/token",
        status=200,
        payload={
            "access_token": "access_token",
            "expires_in": 3600,
            "token_type": "Bearer",
        },
    )

    responses.get(
        "https://connect-api.cloud.huawei.com/api/publish/v2/appid-list?packageName=org.mozilla.focus",
        status=200,
        payload={
            "ret": {"code": 0, "msg": "success"},
            "appids": [],
        },
    )

    with pytest.raises(HagAppInfoException, match="No app found"):
        await run_push_apk(monkeypatch)
