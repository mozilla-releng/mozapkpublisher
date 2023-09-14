from contextlib import contextmanager

from mock import ANY

import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec, MagicMock

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import store
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.push_aab import (
    push_aab,
    main,
)
from unittest.mock import patch


credentials = NamedTemporaryFile()
aab1 = NamedTemporaryFile()
aab2 = NamedTemporaryFile()

AABS = [aab1, aab2]
SERVICE_ACCOUNT = 'foo@developer.gserviceaccount.com'
CLIENT_ID = 'client'
CLIENT_SECRET = 'secret'


def patch_extract_metadata(monkeypatch):
    mock_metadata = {
        aab1: {
            'firefox_build_id': '20171112125738',
            'version_code': '0',
            'package_name': 'org.mozilla.firefox',
            'api_level': 16,
            'firefox_version': '57.0',
        },
        aab2: {
            'firefox_build_id': '20171112125738',
            'version_code': '1',
            'package_name': 'org.mozilla.firefox',
            'api_level': 16,
            'firefox_version': '57.0',
        }
    }
    monkeypatch.setattr('mozapkpublisher.push_aab.extract_aabs_metadata', lambda *args, **kwargs: mock_metadata)
    return mock_metadata


def patch_store_transaction(monkeypatch_, patch_target):
    mock_edit = create_autospec(patch_target)

    @contextmanager
    def fake_transaction(_, __, ___, *, contact_server, dry_run):
        yield mock_edit

    monkeypatch_.setattr(patch_target, 'transaction', fake_transaction)
    return mock_edit


def test_google_no_track():
    with pytest.raises(WrongArgumentGiven):
        push_aab(AABS, SERVICE_ACCOUNT, credentials, track=None)


def test_google(monkeypatch):
    mock_metadata = patch_extract_metadata(monkeypatch)
    edit_mock = patch_store_transaction(monkeypatch, store.GooglePlayEdit)
    push_aab(AABS, SERVICE_ACCOUNT, credentials, 'production', rollout_percentage=50,
             contact_server=False)
    edit_mock.update_aab.assert_called_once_with([
        (aab1, mock_metadata[aab1]),
        (aab2, mock_metadata[aab2]),
    ], 'production', 50)


def test_push_aab_tunes_down_logs(monkeypatch):
    main_logging_mock = MagicMock()
    monkeypatch.setattr('mozapkpublisher.push_aab.main_logging', main_logging_mock)
    monkeypatch.setattr('mozapkpublisher.push_aab.extract_aabs_metadata', MagicMock())
    monkeypatch.setattr('mozapkpublisher.common.utils.metadata_by_package_name', MagicMock())

    push_aab(AABS, SERVICE_ACCOUNT, credentials, 'alpha', contact_server=False)

    main_logging_mock.init.assert_called_once_with()


def test_main_bad_arguments_status_code(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['script'])
    with pytest.raises(SystemExit) as exception:
        main()
    assert exception.value.code == 2


def test_main_google(monkeypatch):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    fail_manual_validation_args = [
        'script',
        '--username', 'foo@developer.gserviceaccount.com',
        '--secret', file,
        'alpha',
        file,
    ]

    with patch.object(mozapkpublisher.push_aab, 'push_aab') as mock_push_aab:
        monkeypatch.setattr(sys, 'argv', fail_manual_validation_args)
        main()

        mock_push_aab.assert_called_once_with(
            ANY,
            'foo@developer.gserviceaccount.com',
            file,
            'alpha',
            None,
            True,
            True,
        )
