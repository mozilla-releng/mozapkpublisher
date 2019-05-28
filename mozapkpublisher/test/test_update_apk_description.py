import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.update_apk_description import main, update_apk_description


credentials = NamedTemporaryFile()


def test_update_apk_description_force_locale(monkeypatch):
    edit_service_mock = create_autospec(googleplay.EditService)
    monkeypatch.setattr(googleplay, 'EditService', lambda _, __, ___, ____, _____: edit_service_mock)
    monkeypatch.setattr(store_l10n, '_translations_per_google_play_locale_code', {
        'google_play_locale': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        }
    })
    monkeypatch.setattr(store_l10n, '_translate_moz_locate_into_google_play_one', lambda locale: 'google_play_locale')

    update_apk_description('org.mozilla.firefox_beta', 'en-US', False, 'foo@developer.gserviceaccount.com', credentials, True)

    edit_service_mock.update_listings.assert_called_once_with(
        'google_play_locale',
        full_description='Long description',
        short_description='Short',
        title='Firefox for Android',
    )

    assert edit_service_mock.update_listings.call_count == 1
    edit_service_mock.commit_transaction.assert_called_once_with()


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.firefox_beta',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()

    complete_args = [
        'script',
        '--package-name', 'org.mozilla.fennec_aurora',
        '--service-account', 'foo@developer.gserviceaccount.com',
        '--credentials', os.path.join(os.path.dirname(__file__), 'data', 'blob')
    ]
    monkeypatch.setattr(sys, 'argv', complete_args)
    monkeypatch.setattr(mozapkpublisher.update_apk_description, 'update_apk_description', lambda _, __, ___, ____, _____, ______: None)
    main()
