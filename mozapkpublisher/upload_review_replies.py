#!/usr/bin/env python3

import argparse
import csv
import logging

from mozapkpublisher.common import googleplay
from mozapkpublisher.common.base import Base

logger = logging.getLogger(__name__)

PACKAGE_NAME = 'org.mozilla.firefox_beta'
EMPTY = '#N/A'
CSV_REPLY_ROW = 2
CSV_REVIEW_ID_ROW = 5


class UploadReviewReplies(Base):

    @classmethod
    def _init_parser(cls):
        cls.parser = argparse.ArgumentParser(
            description="""Bulk upload replies to reviews from the SuMo Playstore tool

    Example for uploading a single CSV_FILE:
    $ python upload_review_replies.py --service-account foo@developer.gserviceaccount.com \
    --credentials key.p12 --replies CSV_FILE""",
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        googleplay.add_general_google_play_arguments(cls.parser)

        cls.parser.add_argument('--replies', dest='reviews_replies_file',
                                type=argparse.FileType(mode='r'),
                                help='Bulk upload given CSV_FILE',
                                required=True)

    def upload_review_replies(self):
        self.review_service = googleplay.ReviewService(
            self.config.service_account, self.config.google_play_credentials_file.name,
            PACKAGE_NAME, contact_google_play=self.config.contact_google_play
        )
        reader = csv.reader(self.config.reviews_replies_file)
        for row in reader:
            if row[0] == EMPTY:
                break
            if row[CSV_REVIEW_ID_ROW] and row[CSV_REPLY_ROW]:
                review_id = row[CSV_REVIEW_ID_ROW]
                reply_text = row[CSV_REPLY_ROW]
                self.upload_single_review_reply(review_id, reply_text)

    def upload_single_review_reply(self, review_id, reply_text):
        r = self.review_service.reply(review_id=review_id, reply_text=reply_text)
        print(r)

    def run(self):
        self.upload_review_replies()


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher.common import main_logging
    main_logging.init()

    UploadReviewReplies().run()


main(__name__)
