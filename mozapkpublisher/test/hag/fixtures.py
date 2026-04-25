from aioresponses import aioresponses
from mozapkpublisher.hag_api import HuaweiAppGalleryApi

import pytest
import pytest_asyncio


@pytest.fixture
def responses_mock():
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def hag():
    async with HuaweiAppGalleryApi("test_client_id", "access_token") as hag:
        yield hag
