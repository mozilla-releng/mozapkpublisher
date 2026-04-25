import aiohttp
import json
from .error import HagAuthenticationException, HagAuthorizationException


async def raise_for_status_with_message(resp: aiohttp.ClientResponse) -> None:
    """
    A wrapper around `raise_for_status` to show the error message returned by the
    Huawei AppGallery Connect API when it's present.

    Note: Huawei returns HTTP 200 with ret.code != 0 for API-level errors,
    so we must check the response body even on 200 responses.

    Note: this will exhaust the request body if it raises an exception
    """
    try:
        body = await resp.json()
    except (aiohttp.ContentTypeError, json.JSONDecodeError):
        if not resp.ok:
            resp.raise_for_status()
        return None

    if resp.ok:
        ret = body.get("ret", {})
        ret_code = ret.get("code", 0)
        if ret_code == 0:
            return None
        error_message = ret.get("msg", f"API error code: {ret_code}")
        if resp.status == 401 or ret_code == 401:
            raise HagAuthenticationException(error_message)
        elif resp.status == 403 or ret_code == 403:
            raise HagAuthorizationException(error_message)
        raise aiohttp.ClientResponseError(
            resp.request_info,
            resp.history,
            status=resp.status,
            message=error_message,
            headers=resp.headers,
        )

    error_message = None
    if "ret" in body:
        error_message = body["ret"].get("msg")

    if error_message is None:
        error_message = body.get("message", resp.reason)

    if resp.status == 401:
        raise HagAuthenticationException(error_message)
    elif resp.status == 403:
        raise HagAuthorizationException(error_message)

    raise aiohttp.ClientResponseError(
        resp.request_info,
        resp.history,
        status=resp.status,
        message=error_message,
        headers=resp.headers,
    )
