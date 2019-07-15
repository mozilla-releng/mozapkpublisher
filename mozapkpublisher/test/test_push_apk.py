from contextlib import contextmanager

from mozapkpublisher.common.exceptions import WrongArgumentGiven

import mozapkpublisher
import os
import pytest
import sys

from unittest.mock import create_autospec, MagicMock

from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay
from mozapkpublisher.common.googleplay import StaticTrack, RolloutTrack, MockGooglePlayConnection
from mozapkpublisher.push_apk import (
    push_apk,
    main,
    _get_ordered_version_codes,
    _split_apk_metadata_per_package_name,
)
from unittest.mock import patch


apk_x86 = NamedTemporaryFile()
apk_arm = NamedTemporaryFile()
APKS = [apk_x86, apk_arm]


@pytest.fixture
def writable_google_play_mock():
    return create_autospec(googleplay.WritableGooglePlay)


def set_up_mocks(monkeypatch_, writable_google_play_mock_):
    def _metadata(*args, **kwargs):
        return {
            apk_arm.name: {
                'architecture': 'armeabi-v7a',
                'firefox_build_id': '20171112125738',
                'version_code': '0',
                'package_name': 'org.mozilla.firefox',
                'locales': (
                    'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                    'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
                    'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                    'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                    'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                    'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                    'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                    'zam', 'zh-CN', 'zh-TW',
                ),
                'api_level': 16,
                'firefox_version': '57.0',
            },
            apk_x86.name: {
                'architecture': 'x86',
                'firefox_build_id': '20171112125738',
                'version_code': '1',
                'package_name': 'org.mozilla.firefox',
                'locales': (
                    'an', 'ar', 'as', 'ast', 'az', 'be', 'bg', 'bn-IN', 'br', 'ca', 'cak', 'cs', 'cy',
                    'da', 'de', 'dsb', 'el', 'en-GB', 'en-US', 'en-ZA', 'eo', 'es-AR', 'es-CL', 'es-ES',
                    'es-MX', 'et', 'eu', 'fa', 'ff', 'fi', 'fr', 'fy-NL', 'ga-IE', 'gd', 'gl', 'gn',
                    'gu-IN', 'he', 'hi-IN', 'hr', 'hsb', 'hu', 'hy-AM', 'id', 'is', 'it', 'ja', 'ka',
                    'kab', 'kk', 'kn', 'ko', 'lo', 'lt', 'lv', 'mai', 'ml', 'mr', 'ms', 'my', 'nb-NO',
                    'nl', 'nn-NO', 'or', 'pa-IN', 'pl', 'pt-BR', 'pt-PT', 'rm', 'ro', 'ru', 'sk', 'sl',
                    'son', 'sq', 'sr', 'sv-SE', 'ta', 'te', 'th', 'tr', 'uk', 'ur', 'uz', 'wo', 'xh',
                    'zam', 'zh-CN', 'zh-TW',
                ),
                'api_level': 16,
                'firefox_version': '57.0',
            }
        }

    @contextmanager
    def fake_transaction(_, __, do_not_commit):
        yield writable_google_play_mock_

    monkeypatch_.setattr(googleplay.WritableGooglePlay, 'transaction', fake_transaction)
    monkeypatch_.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', _metadata)


def test_get_ordered_version_codes():
    assert _get_ordered_version_codes({
        'x86': {
            'version_code': '1'
        },
        'armv7_v15': {
            'version_code': '0'
        }
    }) == ['0', '1']    # should be sorted


def test_upload_apk(writable_google_play_mock, monkeypatch):
    set_up_mocks(monkeypatch, writable_google_play_mock)

    push_apk(APKS, MockGooglePlayConnection(), StaticTrack('alpha'), [])

    for apk_file in (apk_arm, apk_x86):
        writable_google_play_mock.upload_apk.assert_any_call(apk_file.name)

    writable_google_play_mock.update_track.assert_called_once_with(StaticTrack('alpha'), ['0', '1'])


def test_get_distinct_package_name_apk_metadata():
    one_package_apks_metadata = {
        'fennec-1.apk': {'package_name': 'org.mozilla.firefox'},
        'fennec-2.apk': {'package_name': 'org.mozilla.firefox'}
    }

    expected_one_package_metadata = {
        'org.mozilla.firefox': {
            'fennec-1.apk': {'package_name': 'org.mozilla.firefox'},
            'fennec-2.apk': {'package_name': 'org.mozilla.firefox'}
        }
    }

    one_package_metadata = _split_apk_metadata_per_package_name(one_package_apks_metadata)
    assert len(one_package_metadata.keys()) == 1
    assert expected_one_package_metadata == one_package_metadata

    two_package_apks_metadata = {
        'focus-1.apk': {'package_name': 'org.mozilla.focus'},
        'focus-2.apk': {'package_name': 'org.mozilla.focus'},
        'klar.apk': {'package_name': 'org.mozilla.klar'}
    }

    expected_two_package_metadata = {
        'org.mozilla.klar': {
            'klar.apk': {'package_name': 'org.mozilla.klar'}
        },
        'org.mozilla.focus': {
            'focus-1.apk': {'package_name': 'org.mozilla.focus'},
            'focus-2.apk': {'package_name': 'org.mozilla.focus'}
        }
    }

    two_package_metadata = _split_apk_metadata_per_package_name(two_package_apks_metadata)
    assert len(two_package_metadata.keys()) == 2
    assert expected_two_package_metadata == two_package_metadata


def test_push_apk_tunes_down_logs(monkeypatch):
    main_logging_mock = MagicMock()
    monkeypatch.setattr('mozapkpublisher.push_apk.main_logging', main_logging_mock)
    monkeypatch.setattr('mozapkpublisher.push_apk.extract_and_check_apks_metadata', MagicMock())
    monkeypatch.setattr('mozapkpublisher.push_apk._split_apk_metadata_per_package_name', MagicMock())

    push_apk(APKS, MockGooglePlayConnection(), StaticTrack('alpha'), [])

    main_logging_mock.init.assert_called_once_with()


def test_main_bad_arguments_status_code(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['script'])
    with pytest.raises(SystemExit) as exception:
        main()
    assert exception.value.code == 2


@pytest.mark.parametrize('flags', (
        (['--track', 'rollout']),
        (['--track', 'production', '--rollout-percentage', '50']),
        (['--track', 'nightly', '--rollout-percentage', '1']),
))
def test_parse_invalid_track(monkeypatch, flags):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    args = [
        'script',
        '--expected-package-name', 'org.mozilla.fennec_aurora', '--do-not-contact-google-play'
    ] + flags + [file]
    monkeypatch.setattr(sys, 'argv', args)

    with pytest.raises(WrongArgumentGiven):
        main()


@pytest.mark.parametrize('flags,expected_track', (
        (['--track', 'rollout', '--rollout-percentage', '50'], RolloutTrack(0.50)),
        (['--track', 'production'], StaticTrack('production')),
        (['--track', 'nightly'], StaticTrack('nightly')),
))
def test_parse_valid_track(monkeypatch, flags, expected_track):
    file = os.path.join(os.path.dirname(__file__), 'data', 'blob')
    args = [
        'script',
        '--expected-package-name', 'org.mozilla.fennec_aurora', '--do-not-contact-google-play'
    ] + flags + [file]
    monkeypatch.setattr(sys, 'argv', args)

    with patch.object(mozapkpublisher.push_apk, 'push_apk') as mock_push_apk:
        main()
        mock_push_apk.assert_called_once()
        assert mock_push_apk.call_args[0][2] == expected_track


def test_main(monkeypatch):
    incomplete_args = [
        'script', '--expected-package-name', 'org.mozilla.fennec_aurora', '--track', 'alpha',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        main()
