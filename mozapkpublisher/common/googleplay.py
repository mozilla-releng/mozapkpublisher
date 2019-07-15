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
from contextlib import contextmanager

import httplib2
import json
import logging

from apiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.errors import HttpError
# HACK: importing mock in production is useful for option `--do-not-contact-google-play`
from unittest.mock import MagicMock

from mozapkpublisher.common.exceptions import WrongArgumentGiven

logger = logging.getLogger(__name__)


class RolloutTrack:
    def __init__(self, percentage):
        if not (1.0 >= percentage > 0):
            raise ValueError('Rollout percentage must be (0.0, 1.0]')
        self.name = 'rollout'
        self.percentage = percentage

    def __eq__(self, other):
        if isinstance(other, RolloutTrack):
            return self.name == other.name
        return False


class StaticTrack:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if isinstance(other, StaticTrack):
            return self.name == other.name
        return False


def add_general_google_play_arguments(parser):
    parser.add_argument('--service-account', help='The service account email')
    parser.add_argument('--credentials', dest='google_play_credentials_file', type=argparse.FileType(mode='rb'),
                        help='The p12 authentication file')

    parser.add_argument('--commit', action='store_true',
                        help='Commit changes onto Google Play. This action cannot be reverted.')
    parser.add_argument('--do-not-contact-google-play', action='store_false', dest='contact_google_play',
                        help='''Prevent any request to reach Google Play. Use this option if you want to run the script
without any valid credentials nor valid APKs. In fact, Google Play may error out at the first invalid piece of data sent.
--service-account and --credentials must still be provided (you can just fill them with random string and file).''')


class GooglePlayConnection:
    def __init__(self, edit_resource):
        self._edit_resource = edit_resource

    def get_edit_resource(self):
        return self._edit_resource

    @staticmethod
    def open(service_account, credentials_file_path):
        # Create an httplib2.Http object to handle our HTTP requests an
        # authorize it with the Credentials. Note that the first parameter,
        # service_account_name, is the Email address created for the Service
        # account. It must be the email address associated with the key that
        # was created.
        scope = 'https://www.googleapis.com/auth/androidpublisher'
        credentials = ServiceAccountCredentials.from_p12_keyfile(
            service_account,
            credentials_file_path,
            scopes=scope
        )
        http = httplib2.Http()
        http = credentials.authorize(http)

        service = build(serviceName='androidpublisher', version='v3', http=http,
                        cache_discovery=False)

        return GooglePlayConnection(service.edits())


class _ExecuteDummy:
    def __init__(self, return_value):
        self._return_value = return_value

    def execute(self):
        return self._return_value


class MockGooglePlayConnection:
    @staticmethod
    def get_edit_resource():
        edit_service_mock = MagicMock()

        edit_service_mock.insert = lambda *args, **kwargs: _ExecuteDummy(
            {'id': 'fake-transaction-id'})
        edit_service_mock.commit = lambda *args, **kwargs: _ExecuteDummy(None)

        apks_mock = MagicMock()
        apks_mock.upload = lambda *args, **kwargs: _ExecuteDummy(
            {'versionCode': 'fake-version-code'})
        edit_service_mock.apks = lambda *args, **kwargs: apks_mock

        update_mock = MagicMock()
        update_mock.update = lambda *args, **kwargs: _ExecuteDummy('fake-update-response')
        edit_service_mock.tracks = lambda *args, **kwargs: update_mock
        edit_service_mock.listings = lambda *args, **kwargs: update_mock

        return edit_service_mock


def connection_for_options(contact_google_play, service_account, credentials_file):
    if contact_google_play:
        if service_account is None or credentials_file is None:
            raise WrongArgumentGiven("Either provide '--service-account' and '--credentials', or avoid communication "
                                     "with the real Google Play with '--do-not-contact-google-play'")
        return GooglePlayConnection.open(service_account, credentials_file.name)
    else:
        if service_account is not None or credentials_file is not None:
            raise WrongArgumentGiven("When using '--do-not-contact-google-play', do not use '--service-account' or "
                                     "'--credentials'")

        logger.warning('Not a single request to Google Play will be made, since `contact_google_play` was set')
        return MockGooglePlayConnection()


class ReadOnlyGooglePlay:
    """Read-only access to the Google Play store

    Create an instance by calling ReadOnlyGooglePlay.create() instead of using the constructor
    """

    def __init__(self, edit_resource, edit_id, package_name):
        self._edit_resource = edit_resource
        self._edit_id = edit_id
        self._package_name = package_name

    def get_rollout_status(self):
        response = self._edit_resource.tracks().get(
            editId=self._edit_id,
            track='production',
            packageName=self._package_name
        ).execute()
        logger.debug('Track "production" has status: {}'.format(response))
        return response

    @staticmethod
    def create(connection, package_name):
        edit_resource = connection.get_edit_resource()
        edit_id = edit_resource.insert(body={}, packageName=package_name).execute()['id']
        return ReadOnlyGooglePlay(edit_resource, edit_id, package_name)


class WritableGooglePlay(ReadOnlyGooglePlay):
    """Read-write access to the Google Play store

    Create an instance by calling WritableGooglePlay.transaction(), instead of using the
    constructor. This will automatically handle committing the transaction when the "with" block
    ends.

    E.g.: `with WritableGooglePlay.transaction() as google_play:`
    """

    def __init__(self, edit_resource, edit_id, package_name):
        super().__init__(edit_resource, edit_id, package_name)

    def upload_apk(self, apk_path):
        logger.info('Uploading "{}" ...'.format(apk_path))
        try:
            response = self._edit_resource.apks().upload(
                editId=self._edit_id,
                packageName=self._package_name,
                media_body=apk_path
            ).execute()
            logger.info('"{}" uploaded'.format(apk_path))
            logger.debug('Upload response: {}'.format(response))
        except HttpError as e:
            if e.resp['status'] == '403':
                # XXX This is really how data is returned by the googleapiclient.
                error_content = json.loads(e.content)
                errors = error_content['error']['errors']
                if (len(errors) == 1 and errors[0]['reason'] in (
                        'apkUpgradeVersionConflict',
                        'apkNotificationMessageKeyUpgradeVersionConflict'
                )):
                    logger.warning(
                        'APK "{}" has already been uploaded on Google Play. Skipping...'.format(
                            apk_path)
                    )
                    return
            raise

    def update_track(self, track, version_codes):
        body = {
            u'releases': [{
                u'status': 'completed',
                u'versionCodes': version_codes,
            }],
        }

        if isinstance(track, RolloutTrack):
            body[u'userFraction'] = track.percentage

        response = self._edit_resource.tracks().update(
            editId=self._edit_id, track=track.name, packageName=self._package_name, body=body
        ).execute()
        logger.info('Track "{}" updated with: {}'.format(track.name, body))
        logger.debug('Track update response: {}'.format(response))

    def update_listings(self, language, title, full_description, short_description):
        body = {
            'fullDescription': full_description,
            'shortDescription': short_description,
            'title': title,
        }
        response = self._edit_resource.listings().update(
            editId=self._edit_id, packageName=self._package_name, language=language, body=body
        ).execute()
        logger.info(u'Listing for language "{}" has been updated with: {}'.format(language, body))
        logger.debug(u'Listing response: {}'.format(response))

    @staticmethod
    @contextmanager
    def transaction(connection, package_name, commit):
        edit_resource = connection.get_edit_resource()
        edit_id = edit_resource.insert(body={}, packageName=package_name).execute()['id']
        google_play = WritableGooglePlay(edit_resource, edit_id, package_name)
        yield google_play
        if commit:
            edit_resource.commit(editId=edit_id, packageName=package_name)
            logger.info('Changes committed')
            logger.debug('edit_id "{}" for "{}" has been committed'.format(edit_id, package_name))
        else:
            logger.warning('Transaction not committed, since `do_not_commit` was set')
