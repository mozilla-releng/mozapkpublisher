from typing import Dict, Any, List, Optional
from .utils import raise_for_status_with_message
from .auth import create_access_token
from .error import HagUploadException, HagAppInfoException, HagSubmitException
from urllib.parse import urljoin

import aiohttp
import logging
import os.path

BASE_API_URL = "https://connect-api.cloud.huawei.com/"
logger = logging.getLogger(__name__)


class HuaweiAppGalleryStore:
    """
    High level wrapper to make actions on applications on the Huawei AppGallery Connect store
    """

    def __init__(self, client_id: str, client_secret: str, dry_run: bool = False):
        self._client_id = client_id
        self._client_secret = client_secret
        self._dry_run = dry_run
        self.api: Optional[HuaweiAppGalleryApi] = None

    async def __aenter__(self) -> "HuaweiAppGalleryStore":
        access_token = await create_access_token(self._client_id, self._client_secret)
        self.api = HuaweiAppGalleryApi(self._client_id, access_token)
        await self.api.__aenter__()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self.api:
            await self.api.__aexit__(*args)

    async def upload_apks(self, package_name, apks, rollout_percentage, submit=False):
        """
        Upload the APKs passed as arguments. The app to be updated will be inferred from the package name.
        If rollout_percentage is not None, the submission will use a phased rollout at that rate.
        """
        if self._dry_run:
            logger.warning('No APKs were uploaded since `dry_run` was `True`')
            return

        app_id = await self.api.get_app_id(package_name)

        file_infos = []
        for apk in apks:
            fd, metadata = apk
            file_dest_url = await self.upload_file(app_id, fd.name)
            file_infos.append({
                "fileName": os.path.basename(fd.name),
                "fileDestUrl": file_dest_url,
            })

        await self.api.update_app_file_info(app_id, file_infos)

        if submit:
            release_type = 3 if rollout_percentage is not None else 1
            phased_percent = rollout_percentage if rollout_percentage is not None else None
            await self.api.submit_app(app_id, release_type=release_type, phased_percent=phased_percent)

    async def upload_file(self, app_id: str, file_path: str) -> str:
        """
        Orchestrates getting an upload URL, uploading the file, and returning the fileDestUrl.
        """
        upload_info = await self.api.get_upload_url(app_id, suffix="apk")
        upload_url = upload_info["uploadUrl"]
        auth_code = upload_info["authCode"]

        file_info = await self.api.upload_file(upload_url, auth_code, file_path)
        return file_info["fileDestUrl"]


class HuaweiAppGalleryApi:
    """
    A low level wrapper around the Huawei AppGallery Connect API.
    You should probably use the `HuaweiAppGalleryStore` wrapper around this instead.
    """

    def __init__(self, client_id: str, access_token: str):
        self._client_id = client_id
        self._access_token = access_token
        self._client = aiohttp.ClientSession()

    async def __aenter__(self) -> "HuaweiAppGalleryApi":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self._client.close()

    def _default_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "client_id": self._client_id,
        }

    async def _request(
        self,
        method: str,
        route: str,
        *,
        base_url: str = BASE_API_URL,
        **kwargs: Any,
    ) -> Any:
        headers = self._default_headers()
        url = urljoin(base_url, route)

        response = await self._client.request(method, url, headers=headers, **kwargs)

        await raise_for_status_with_message(response)

        body = await response.json()
        return body

    async def get_app_id(self, package_name: str) -> str:
        """
        Get the Huawei app ID for a given package name.

        https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-getappidbyname-0000001944025825
        """
        result = await self._request(
            "GET",
            "/api/publish/v2/appid-list",
            params={"packageName": package_name},
        )

        appids = result.get("appids", [])
        if not appids:
            raise HagAppInfoException(
                f"No app found for package name: {package_name}"
            )

        return appids[0]["value"]

    async def get_upload_url(self, app_id: str, suffix: str = "apk") -> Dict[str, Any]:
        """
        Get a pre-authorized upload URL from Huawei's file server.

        https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-getuploadurl-0000001944025829
        """
        result = await self._request(
            "GET",
            "/api/publish/v2/upload-url",
            params={"appId": app_id, "suffix": suffix},
        )

        return result

    async def upload_file(
        self, upload_url: str, auth_code: str, file_path: str
    ) -> Dict[str, Any]:
        """
        Upload a file to Huawei's file server using the pre-authorized URL.

        Note: this goes to the external Huawei file server, not through _request.
        """
        headers = self._default_headers()

        form = aiohttp.FormData()
        form.add_field("authCode", auth_code)
        with open(file_path, "rb") as file:
            form.add_field(
                "file", file, filename=os.path.basename(file_path)
            )

            response = await self._client.post(upload_url, headers=headers, data=form)

        await raise_for_status_with_message(response)
        body = await response.json()

        result = body.get("result", {})
        upload_rsp = result.get("UploadFileRsp", {})
        file_info_list = upload_rsp.get("fileInfoList", [])

        if not file_info_list:
            raise HagUploadException(
                f"Upload succeeded but no file info returned for {file_path}"
            )

        return file_info_list[0]

    async def update_app_file_info(
        self, app_id: str, files: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Register uploaded files with the app.

        https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-updatefileinfo-0000001944025833
        """
        data = {
            "fileType": 5,
            "files": files,
        }

        return await self._request(
            "PUT",
            "/api/publish/v2/app-file-info",
            params={"appId": app_id},
            json=data,
        )

    async def get_app_info(self, app_id: str) -> Dict[str, Any]:
        """
        Get full app metadata.

        https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-queryappinfo-0000001944025837
        """
        return await self._request(
            "GET",
            "/api/publish/v2/app-info",
            params={"appId": app_id},
        )

    async def submit_app(
        self,
        app_id: str,
        release_type: int = 1,
        phased_percent: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Submit the app for review.

        https://developer.huawei.com/consumer/en/doc/harmonyos-references/appgallerykit-submitapp-0000001944025841

        release_type: 1 = full release, 3 = phased release
        phased_percent: percentage for phased release (1-100), only used when release_type=3
        """
        data: Dict[str, Any] = {"releaseType": release_type}

        if release_type == 3 and phased_percent is not None:
            data["phasedReleasePercent"] = phased_percent

        return await self._request(
            "POST",
            "/api/publish/v2/app-submit",
            params={"appId": app_id},
            json=data,
        )
