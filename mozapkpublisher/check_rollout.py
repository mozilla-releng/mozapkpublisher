#!/usr/bin/env python3

import calendar
import email.utils as eu
import logging
import time

import requests

from argparse import ArgumentParser
from mozapkpublisher.common.googleplay import add_general_google_play_arguments, \
    ReadOnlyGooglePlay, connection_for_options

DAY = 24 * 60 * 60

logger = logging.getLogger(__name__)


def check_rollout(google_play, days):
    """Check if package_name has a release on staged rollout for too long"""
    track_status = google_play.get_rollout_status()
    releases = track_status['releases']
    for release in releases:
        if release['status'] == 'inProgress':
            url = 'https://archive.mozilla.org/pub/mobile/releases/{}/SHA512SUMS'.format(release['name'])
            resp = requests.head(url)
            if resp.status_code != 200:
                if resp.status_code != 404:  # 404 is expected for release candidates
                    logger.warning("Could not check %s: %s", url, resp.status_code)
                continue
            age = time.time() - calendar.timegm(eu.parsedate(resp.headers['Last-Modified']))
            if age >= days * DAY:
                yield release, age


def main():
    parser = ArgumentParser(description='Check for in-progress Firefox for Android staged rollout')
    add_general_google_play_arguments(parser)
    parser.add_argument('--days', help='The time before we warn about incomplete staged rollout of a release (default: 7)',
                        type=int, default=7)
    config = parser.parse_args()
    connection = connection_for_options(config.contact_google_play, config.service_account,
                                        config.google_play_credentials_file)

    google_play = ReadOnlyGooglePlay.create(connection, 'org.mozilla.firefox')
    for (release, age) in check_rollout(google_play, config.days):
        print('fennec {} is on staged rollout at {}% but it shipped {} days ago'.format(
              release['name'], int(release['userFraction'] * 100), int(age / DAY)))


__name__ == '__main__' and main()
