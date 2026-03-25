from typing import cast

import aiohttp
from .utils import raise_for_status_with_message


async def create_access_token(client_id: str, client_secret: str) -> str:
    """
    Obtain an access token from the Huawei AppGallery Connect API using
    OAuth2 client_credentials grant.

    https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-gettoken-0000001944025821
    """
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://connect-api.cloud.huawei.com/api/oauth2/v1/token",
            json=data,
        ) as resp:
            await raise_for_status_with_message(resp)

            result = await resp.json()

            return cast(str, result["access_token"])
