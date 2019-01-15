import aiohttp
import pytest
import requests
import tempfile

from aioresponses import aioresponses
from unittest.mock import MagicMock

from mozapkpublisher.common.utils import load_json_url, file_sha512sum, download_file, get_firefox_package_name


def test_load_json_url(monkeypatch):
    response_mock = MagicMock()
    response_mock.json = MagicMock()
    monkeypatch.setattr(requests, 'get', lambda url: response_mock)
    load_json_url('https://dummy-url.tld')
    response_mock.json.assert_called_once_with()


@pytest.mark.asyncio
async def test_download_file():
    with aioresponses() as mocked:
        origin_data = b'a' * 1025
        mocked.get('https://dummy-url.tld/file', status=200, body=origin_data, headers={'content-length': '0'})
        with tempfile.NamedTemporaryFile() as temp_file:
            async with aiohttp.ClientSession() as session:
                await download_file(session, 'https://dummy-url.tld/file', temp_file.name)
            temp_file.seek(0)
            data = temp_file.read()

        assert data == origin_data


def test_file_sha512sum():
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(b'known sha512')
        temp_file.seek(0)

        assert file_sha512sum(temp_file.name) == '0b1622c08ae1fcffe9f0d1dd17fe273d7e8c96668981c8a38f6bbfa4f757b30af0\
ed2aabf90f1f8a5983082a0b88194fe81bc850d3019fd9eca9328584227c84'


@pytest.mark.parametrize('version, expected', (
    ('66.0a1', 'org.mozilla.fennec_aurora'),
    ('66.0b2', 'org.mozilla.firefox_beta'),
    ('66.0', 'org.mozilla.firefox'),
))
def test_get_firefox_package_name(version, expected):
    assert get_firefox_package_name(version) == expected


def test_bad_get_firefox_package_name():
    with pytest.raises(ValueError):
        get_firefox_package_name('66.0esr')
