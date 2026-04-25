import pytest
from unittest.mock import AsyncMock, patch
from mozapkpublisher.hag_api import HuaweiAppGalleryStore


@pytest.mark.asyncio
async def test_hag_dry_run(responses_mock):
    # Having the `responses_mock` fixture in the test makes sure that this whole test doesn't try to contact any server
    # Patch create_access_token since dry_run still calls __aenter__ which obtains a token
    with patch("mozapkpublisher.hag_api.create_access_token", new_callable=AsyncMock, return_value="fake_token"):
        async with HuaweiAppGalleryStore("test_client_id", "test_client_secret", dry_run=True) as hag:
            await hag.upload_apks('org.mozilla.firefox', [], None)
