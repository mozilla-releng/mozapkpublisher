#!/usr/bin/env python3

import argparse
import asyncio

from mozapkpublisher.hag_api.auth import create_access_token


async def main(args: argparse.Namespace) -> None:
    print(await create_access_token(args.client_id, args.client_secret))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("client_id")
    parser.add_argument("client_secret")

    args = parser.parse_args()
    asyncio.run(main(args))
