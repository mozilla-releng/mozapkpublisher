#!/usr/bin/env python3

import argparse
import csv
import logging

from mozapkpublisher.common import googleplay, store_l10n
from mozapkpublisher.common.base import Base

logger = logging.getLogger(__name__)

MAX_BULK_SIZE = 500


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

        cls.parser.add_argument('--package-name',
                                choices=store_l10n.STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys(),
                                help='The APK package name', required=True)
        cls.parser.add_argument('--replies', dest='reviews_replies_file',
                                type=argparse.FileType(mode='r'),
                                help='Bulk upload given CSV_FILE',
                                required=True)
        cls.parser.add_argument('--csv-columns',
                                nargs=2, type=int, default=[0, 1],
                                help='Set the REPLY_COLUMN and REVIEW_ID_COLUMN',
                                metavar=('REPLY_COLUMN', 'REVIEW_ID_COLUMN'),
                                required=False)
        cls.parser.add_argument('--id-blacklist', dest='review_id_blacklist_file',
                                type=argparse.FileType(mode='r'),
                                help='Log IDs to skip',
                                required=False)
        cls.parser.add_argument('--id-log', dest='review_id_log_file',
                                type=argparse.FileType(mode='a'),
                                help='Log IDs of uploaded replies',
                                required=False)

    def upload_review_replies(self):
        self.review_service = googleplay.ReviewService(
            self.config.service_account, self.config.google_play_credentials_file.name,
            self.config.package_name, contact_google_play=self.config.contact_google_play
        )
        reader = csv.reader(self.config.reviews_replies_file)
        count = 0
        if self.config.review_id_blacklist_file:
            blacklist = set(line.strip()
                            for line in self.config.review_id_blacklist_file.readlines())
        else:
            blacklist = set()

        csv_reply_column = self.config.csv_columns[0]
        csv_review_id_column = self.config.csv_columns[1]

        # skip header
        next(reader)
        for row in reader:
            if count >= MAX_BULK_SIZE:
                logger.info("Uploaded {} replies. Stopping!".format(count))
                break
            if row[csv_review_id_column] and row[csv_reply_column]:
                review_id = row[csv_review_id_column]
                reply_text = row[csv_reply_column]
                if review_id in blacklist:
                    logger.info("blacklisted {}".format(review_id))
                    continue
                self.upload_single_review_reply(review_id, reply_text)
                count += 1

    def upload_single_review_reply(self, review_id, reply_text):
        r = self.review_service.reply(review_id=review_id, reply_text=reply_text)
        self.log_id(review_id)
        logger.info(r)

    def log_id(self, id):
        if self.config.review_id_log_file:
            self.config.review_id_log_file.write("{}\n".format(id))

    def run(self):
        self.upload_review_replies()


def main(name=None):
    if name not in ('__main__', None):
        return

    from mozapkpublisher.common import main_logging
    main_logging.init()

    UploadReviewReplies().run()


main(__name__)