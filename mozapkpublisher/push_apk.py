#!/usr/bin/env python

import sys
import argparse
import logging

from oauth2client import client

from mozapkpublisher import googleplay
from mozapkpublisher.apk_metadata import extract_metadata_from_apk
from mozapkpublisher.base import Base
from mozapkpublisher.exceptions import WrongArgumentGiven
from mozapkpublisher.storel10n import StoreL10n

logger = logging.getLogger(__name__)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise WrongArgumentGiven(message)


class PushAPK(Base):
    def __init__(self, config=None):
        self.config = self._parse_config(config)
        if self.config.track == 'rollout' and self.config.rollout_percentage is None:
            raise WrongArgumentGiven("When using track='rollout', rollout percentage must be provided too")

        self.translationMgmt = StoreL10n()

    @classmethod
    def _init_parser(cls):
        cls.parser = ArgumentParser(
            description='''Upload Firefox for Android APKs onto Google Play Store.

    Example for Firefox for Android Beta:
    $ python push_apk.py --package-name org.mozilla.firefox_beta --track production \
--service-account foo@developer.gserviceaccount.com --credentials key.p12 \
--apk-x86=/path/to/fennec-XX.0bY.multi.android-i386.apk \
--apk-armv7-v15=/path/to/fennec-XX.0bY.multi.android-arm-v15.apk''',
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        googleplay.add_general_google_play_arguments(cls.parser)

        cls.parser.add_argument('--no-commit', dest='should_commit', action='store_false', default=True,
                                help='''Perform every operation of the transation, except committing. No data will be
stored on Google Play. Use this option if you want to test the script with the same data more than once.''')

        cls.parser.add_argument('--track', choices=googleplay.TRACK_VALUES, default='alpha',
                                help='Track on which to upload')
        cls.parser.add_argument('--untrack-old', action='store_true', default=False,
                                help='''Unpublish older builds on lower tracks.

Context: The Google Play Developer API does not allow to publish a beta version if there is an alpha version with a
lower version code. If you want to publish to another higher track and automatically disable from another track,
toggle this flag on.''')

        cls.parser.add_argument('--rollout-percentage', type=int, choices=range(0, 101), metavar='[0-100]',
                                default=None,
                                help='The percentage of user who will get the update. Specify only if track is rollout')

        cls.parser.add_argument('--apk-x86', dest='apk_file_x86', type=argparse.FileType(),
                                help='The path to the x86 APK file', required=True)
        cls.parser.add_argument('--apk-armv7-v15', dest='apk_file_armv7_v15', type=argparse.FileType(),
                                help='The path to the ARM v7 API v15 APK file', required=True)

    def upload_apks(self, service, apk_files):
        """ Upload the APK to google play

        service -- The session to Google play
        apk_files -- The files
        """
        metadata_per_apks = {apk_file.name: extract_metadata_from_apk(apk_file.name) for apk_file in apk_files}
        self._verify_package_names(metadata_per_apks)
        self.translationMgmt.load_mapping()

        edit_id = service.edits().insert(body={}, packageName=self.config.package_name).execute()['id']
        self._upload_without_committing(service, edit_id, apk_files, metadata_per_apks)
        self._upload_whats_new_if_possible(service, edit_id, apk_files, metadata_per_apks)
        self._update_tracks(service, edit_id, metadata_per_apks)
        self._commit_if_needed(service, edit_id)

    def _verify_package_names(self, metadata_per_apks):
        for apk, metadata in metadata_per_apks.items():
            package_name = metadata['package_name']
            if package_name != self.config.package_name:
                raise Exception('Metadata for "{}" reads package name "{}", whereas "{}" was specified'.format(
                    apk, package_name, self.config.package_name
                ))
        logger.debug('All packages reference the same package name: {}'.format(self.config.package_name))

    def _upload_without_committing(self, service, edit_id, apk_files, metadata_per_apks):
        for apk_file in apk_files:
            apk_file_name = apk_file.name
            try:
                apk_response = service.edits().apks().upload(
                    editId=edit_id,
                    packageName=self.config.package_name,
                    media_body=apk_file_name
                ).execute()
                version_code = self._sanity_check_version_code(metadata_per_apks, apk_file_name, apk_response)

                logger.info('"{}" (version code: {}) has been transfered to Google Play Store. Nothing will be published \
until committed'.format(apk_file_name, version_code))

            except client.AccessTokenRefreshError:
                logger.critical('The credentials have been revoked or expired,'
                                'please re-run the application to re-authorize')

    def _sanity_check_version_code(self, metadata_per_apks, apk_file_name, play_store_response):
        apk_version_code = metadata_per_apks[apk_file_name]['version_code']
        playstore_version_code = play_store_response['versionCode']

        if apk_version_code != playstore_version_code:
            raise Exception('Google Play reported version code "{}" for "", whereas "{}" was read locally'.format(
                apk_version_code, apk_file_name, playstore_version_code
            ))
        return apk_version_code

    def _upload_whats_new_if_possible(self, service, edit_id, apk_files, metadata_per_apks):
        if 'aurora' in self.config.package_name:
            logger.warning('Aurora is not supported by the L10n Store (see \
https://github.com/mozilla-l10n/stores_l10n/issues/71). Skipping what\'s new.')
            return

        for apk_file in apk_files:
            self._push_whats_new(service, edit_id, version_code=metadata_per_apks[apk_file.name]['version_code'])

    def _push_whats_new(self, service, edit_id, version_code):
        package_code = googleplay.PACKAGE_NAME_VALUES[self.config.package_name]
        locales = self.translationMgmt.get_list_locales(package_code)
        locales.append(u'en-US')

        for locale in locales:
            translation = self.translationMgmt.get_translation(package_code, locale)
            whatsnew = translation.get("whatsnew")
            if locale == "en-GB":
                logger.info("Ignoring en-GB as locale")
                continue
            locale = self.translationMgmt.locale_mapping(locale)
            logger.info('Locale "%s" what\'s new has been updated to "%s"'
                        % (locale, whatsnew))

            listing_response = service.edits().apklistings().update(
                editId=edit_id, packageName=self.config.package_name, language=locale,
                apkVersionCode=version_code,
                body={'recentChanges': whatsnew}).execute()

            logger.info('Listing for language %s was updated.' % listing_response['language'])

    def _update_tracks(self, service, edit_id, metadata_per_apks):
        tracks_to_update = googleplay.get_lower_to_initial_tracks(self.config.track) if self.config.untrack_old \
            else [self.config.track]

        for track_name in tracks_to_update:
            track = service.edits().tracks().get(
                packageName=self.config.package_name, editId=edit_id, track=track_name
            ).execute()

            already_published_version_codes = track['versionCodes']

            if track_name == self.config.track or self._are_published_version_codes_lower(
                published_version_codes=already_published_version_codes,
                new_version_codes=self._version_codes_as_list(metadata_per_apks)
            ):
                service.edits().tracks().update(
                    editId=edit_id,
                    track=track_name,
                    packageName=self.config.package_name,
                    body=self._craft_upload_body(track_name, metadata_per_apks)
                ).execute()
                logger.info('Track "{}" set to version codes {}'.format(track_name, metadata_per_apks))
            else:
                logger.warn(
                    'Skipping track "{}". It already has more recent version codes ({}) than the local ones: {}'
                    .format(track_name, already_published_version_codes, metadata_per_apks)
                )

    def _version_codes_as_list(self, metadata_per_apks):
        return [metadata['version_code'] for metadata in metadata_per_apks.values()]

    def _are_published_version_codes_lower(self, published_version_codes, new_version_codes):
        # Google Play doesn't tell what version code is mapped to which architecture. Because this script is meant to
        # be run against nightlies, we make the assumption that no new version code is smaller than the ones already
        # published.
        is_every_published_version_code_lower = all(
            published_code < new_code
            for published_code in published_version_codes
            for new_code in new_version_codes
        )

        is_every_published_version_code_higher_or_equal = all(
            published_code >= new_code
            for published_code in published_version_codes
            for new_code in new_version_codes
        )

        if is_every_published_version_code_lower == is_every_published_version_code_higher_or_equal:
            raise Exception(
                'Some version codes ({}) are at the same time smaller and bigger than the ones already published ({})'
                .format(new_version_codes, published_version_codes)
            )

    def _craft_upload_body(self, track_name, metadata_per_apks):
        upload_body = {u'versionCodes': self._version_codes_as_list(metadata_per_apks)}
        if track_name == 'rollout':
            upload_body[u'userFraction'] = self.config.rollout_percentage / 100
        return upload_body

    def _commit_if_needed(self, service, edit_id):
        if self.config.should_commit:
            service.edits().commit(
                editId=edit_id, packageName=self.config.package_name
            ).execute()
            logger.info('Changes committed')
        else:
            logger.warn('No-commit option was given, transaction not committed.')

    def run(self):
        """ Upload the APK files """
        service = googleplay.connect(self.config.service_account, self.config.google_play_credentials_file.name)
        apks = (self.config.apk_file_armv7_v15, self.config.apk_file_x86)
        self.upload_apks(service, apks)


if __name__ == '__main__':
    from mozapkpublisher import main_logging
    main_logging.init()

    try:
        push_apk = PushAPK()
        push_apk.run()
    except WrongArgumentGiven as e:
        PushAPK.parser.print_help(sys.stderr)
        sys.stderr.write('{}: error: {}\n'.format(PushAPK.parser.prog, e))
        sys.exit(2)
