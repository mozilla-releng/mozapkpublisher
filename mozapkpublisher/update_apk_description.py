#!/usr/bin/env python3

import argparse
import logging

from argparse import ArgumentParser
from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common.googleplay import connection_for_options, WritableGooglePlay

logger = logging.getLogger(__name__)


def update_apk_description(connection, package_name, force_locale, commit):
    with WritableGooglePlay.transaction(connection, package_name, commit) as google_play:
        moz_locales = [force_locale] if force_locale else None
        l10n_strings = store_l10n.get_translations_per_google_play_locale_code(package_name, moz_locales)
        create_or_update_listings(google_play, l10n_strings)


def create_or_update_listings(google_play, l10n_strings):
    for google_play_locale_code, translation in l10n_strings.items():
        google_play.update_listings(
            google_play_locale_code,
            full_description=translation['long_desc'],
            short_description=translation['short_desc'],
            title=translation['title'],
        )
    logger.info('Listing updated for {} locale(s)'.format(len(l10n_strings)))


def main():
    from mozapkpublisher.common import main_logging
    main_logging.init()

    parser = ArgumentParser(
        description="""Update the descriptions of an application (multilang)

        Example for updating beta:
        $ python update_apk_description.py --service-account foo@developer.gserviceaccount.com \
        --package-name org.mozilla.firefox_beta --credentials key.p12""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    googleplay.add_general_google_play_arguments(parser)
    parser.add_argument('--package-name', choices=store_l10n.STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                        help='The Google play name of the app', required=True)
    parser.add_argument('--force-locale', help='Force to a specific locale (instead of all)')
    config = parser.parse_args()
    connection = connection_for_options(config.contact_google_play, config.service_account,
                                        config.google_play_credentials_file)
    update_apk_description(connection, config.package_name, config.force_locale, config.commit)


__name__ == '__main__' and main()
