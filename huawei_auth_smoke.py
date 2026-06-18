#!/usr/bin/env python3
"""
Scratch: Huawei AppGallery auth smoke test (testing-ladder rung #2). NOT for commit.

Read-only. Exercises the real production path -- HuaweiAppGalleryApi -> shared
request() -> create_jwt() -- with a single GET (app_id_list), which is exactly what
infer_app_id_from_package_name() calls during a real upload. Confirms the self-signed
PS256 JWT is accepted with no client_id header / no token-exchange. A 401 here is the
signal we need a token-exchange step.

    uv run python huawei_auth_smoke.py --credentials <private.json> --package-name org.mozilla.firefox
"""
import argparse
import asyncio
import json

from mozapkpublisher.huawei_api import HuaweiAppGalleryApi
from mozapkpublisher.huawei_api.auth import load_credentials


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--credentials", required=True, help="Path to the Service Account private.json")
    parser.add_argument("--package-name", required=True, help="Package name to look up (e.g. org.mozilla.firefox)")
    args = parser.parse_args()

    credentials = load_credentials(args.credentials)
    async with HuaweiAppGalleryApi(credentials) as api:
        result = await api.app_id_list(package_name=args.package_name)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
