""" googleplay.py

    The way to get the API access is to
      1) login in in the Google play admin
      2) Settings
      3) API Access
      4) go in the Google Developers Console
      5) Create "New client ID"
         or download the p12 key (it should remain
         super private)
      6) Move the file in this directory with the name
         'key.p12' or use the --credentials option
"""

import argparse
import httplib2
import logging

from oauth2client.service_account import ServiceAccountCredentials
from apiclient.discovery import build

from mozapkpublisher.exceptions import NoTransactionError, WrongArgumentGiven
from mozapkpublisher.store_l10n import STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME

# Google play has currently 3 tracks. Rollout deploys
# to a limited percentage of users
TRACK_VALUES = ('production', 'beta', 'alpha', 'rollout')


logger = logging.getLogger(__name__)


def add_general_google_play_arguments(parser):
    parser.add_argument('--package-name', choices=STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                        help='The Google play name of the app', required=True)

    parser.add_argument('--service-account', help='The service account email', required=True)
    parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'),
                        default='key.p12', help='The p12 authentication file', required=True)

    parser.add_argument('--dry-run', action='store_true',
                        help='''Perform every operation of the transation, except committing. No data will be
stored on Google Play. Use this option if you want to test the script with the same data more than once.''')


def is_package_name_nightly(package_name):
    # Due to project Dawn, Nightly is now using the Aurora package name.
    # See https://bugzilla.mozilla.org/show_bug.cgi?id=1357351
    return package_name == 'org.mozilla.fennec_aurora'


class EditService(object):
    def __init__(self, service_account, credentials_file_path, package_name, dry_run=True):
        general_service = _connect(service_account, credentials_file_path)
        self._service = general_service.edits()
        self._package_name = package_name
        self._dry_run = dry_run
        self.start_new_transaction()

    def start_new_transaction(self):
        result = self._service.insert(body={}, packageName=self._package_name).execute()
        self._edit_id = result['id']

    def transaction_required(method):
        def _transaction_required(*args, **kwargs):
            edit_service = args[0]
            if edit_service._edit_id is None:
                raise NoTransactionError(edit_service._package_name)

            return method(*args, **kwargs)
        return _transaction_required

    @transaction_required
    def commit_transaction(self):
        if not self._dry_run:
            self._service.commit(editId=self._edit_id, packageName=self._package_name).execute()
            logger.info('Changes committed')
            logger.debug('edit_id "{}" for package "{}" has been committed'.format(self._edit_id, self._package_name))
        else:
            logger.warn('Dry run option was given, transaction not committed.')

        self._edit_id = None

    @transaction_required
    def upload_apk(self, apk_path):
        logger.info('Uploading "{}"'.format(apk_path))
        response = self._service.apks().upload(
            editId=self._edit_id,
            packageName=self._package_name,
            media_body=apk_path
        ).execute()
        logger.info('"{}" uploaded'.format(apk_path))
        logger.debug('Upload response: {}'.format(response))
        return response

    @transaction_required
    def update_track(self, track, version_codes, rollout_percentage=None):
        body = {u'versionCodes': version_codes}
        if rollout_percentage is not None:
            if rollout_percentage < 0 or rollout_percentage > 100:
                raise WrongArgumentGiven('rollout percentage must be between 0 and 100. Value given: {}'.format(rollout_percentage))

            body[u'userFraction'] = rollout_percentage / 100.0  # Ensure float in Python 2

        response = self._service.tracks().update(
            editId=self._edit_id, track=track, packageName=self._package_name, body=body
        ).execute()
        logger.info('Track "{}" updated with: {}'.format(track, body))
        logger.debug('Track update response: {}'.format(response))

    @transaction_required
    def update_listings(self, language, title, full_description, short_description):
        body = {
            'fullDescription': full_description,
            'shortDescription': short_description,
            'title': title,
        }
        response = self._service.listings().update(
            editId=self._edit_id, packageName=self._package_name, language=language, body=body
        ).execute()
        logger.info(u'Listing for language "{}" has been updated with: {}'.format(language, body))
        logger.debug(u'Listing response: {}'.format(response))

    @transaction_required
    def update_whats_new(self, language, apk_version_code, whats_new):
        response = self._service.apklistings().update(
            editId=self._edit_id, packageName=self._package_name, language=language,
            apkVersionCode=apk_version_code, body={'recentChanges': whats_new}
        ).execute()
        logger.info(u'What\'s new listing for ("{}", "{}") has been updated to: "{}"'.format(
            language, apk_version_code, whats_new
        ))
        logger.debug(u'Apk listing response: {}'.format(response))


def _connect(service_account, credentials_file_path):
    """ Connect to the google play interface
    """

    # Create an httplib2.Http object to handle our HTTP requests an
    # authorize it with the Credentials. Note that the first parameter,
    # service_account_name, is the Email address created for the Service
    # account. It must be the email address associated with the key that
    # was created.
    scope = 'https://www.googleapis.com/auth/androidpublisher'
    credentials = ServiceAccountCredentials.from_p12_keyfile(service_account, credentials_file_path, scopes=scope)
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build('androidpublisher', 'v2', http=http, cache_discovery=False)

    return service
