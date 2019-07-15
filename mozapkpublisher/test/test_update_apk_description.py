import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common.exceptions import WrongArgumentGiven
from mozapkpublisher.common.googleplay import MockGooglePlayConnection
from mozapkpublisher.update_apk_description import main, update_apk_description


credentials = NamedTemporaryFile()


def test_update_apk_description_force_locale(monkeypatch):
    google_play_mock = create_autospec(googleplay.WritableGooglePlay)
    monkeypatch.setattr(googleplay, 'WritableGooglePlay', lambda _, __, ___: google_play_mock)
    monkeypatch.setattr(store_l10n, '_translations_per_google_play_locale_code', {
        'google_play_locale': {
            'title': 'Firefox for Android',
            'long_desc': 'Long description',
            'short_desc': 'Short',
            'whatsnew': 'Check out this cool feature!',
        }
    })
    monkeypatch.setattr(store_l10n, '_translate_moz_locate_into_google_play_one', lambda locale: 'google_play_locale')

    update_apk_description(MockGooglePlayConnection(), 'org.mozilla.firefox_beta', 'en-US', False)

    google_play_mock.update_listings.assert_called_once_with(
        'google_play_locale',
        full_description='Long description',
        short_description='Short',
        title='Firefox for Android',
    )

    assert google_play_mock.update_listings.call_count == 1


def test_main(monkeypatch):
    incomplete_args = [
        'script',
        '--package-name', 'org.mozilla.firefox_beta',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(WrongArgumentGiven):
        main()

    complete_args = [
        'script',
        '--package-name', 'org.mozilla.fennec_aurora',
        '--service-account', 'foo@developer.gserviceaccount.com',
        '--credentials', os.path.join(os.path.dirname(__file__), 'data', 'blob')
    ]
    monkeypatch.setattr(sys, 'argv', complete_args)
    monkeypatch.setattr(mozapkpublisher.update_apk_description, 'update_apk_description', lambda _, __, ___, ____: None)
    monkeypatch.setattr(mozapkpublisher.update_apk_description, 'connection_for_options', lambda _, __, ___: None)
    main()
