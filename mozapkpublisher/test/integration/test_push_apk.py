import os
import tempfile

from mozapkpublisher.push_apk import PushAPK
from mozapkpublisher.test import DATA_DIR, skip_when_no_network


APKS_FULL_PATHS = [
    os.path.join(DATA_DIR, file_name)
    for file_name in ('fennec-61.0.multi.android-i386.apk', 'fennec-61.0.multi.android-arm.apk')
]


GOOGLE_PLAY_STRINGS_PATH = os.path.join(DATA_DIR, 'fennec-61.0-google-play-strings.json')


DEFAULT_CONFIG = {
    'service_account': 'dummy-service-account@iam.gserviceaccount.com',
    'track': 'alpha',
    'update_gp_strings_from_file': GOOGLE_PLAY_STRINGS_PATH,
    'do_not_contact_google_play': True,
    '*args': APKS_FULL_PATHS,
}


def test_push_apk_performs_sanity_checks():
    with tempfile.NamedTemporaryFile() as fake_credentials:
        config = {
            **DEFAULT_CONFIG,
            'credentials': fake_credentials.name,
        }
        PushAPK(config).run()


@skip_when_no_network
def test_push_apk_downloads_strings():
    with tempfile.NamedTemporaryFile() as fake_credentials:
        config = {
            **DEFAULT_CONFIG,
            'update_gp_strings_from_l10n_store': True,
            'credentials': fake_credentials.name,
        }
        del config['update_gp_strings_from_file']
        PushAPK(config).run()
