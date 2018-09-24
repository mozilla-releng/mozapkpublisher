import pytest
import os
import sys

from unittest.mock import create_autospec

from copy import copy
from tempfile import NamedTemporaryFile

from mozapkpublisher.common import googleplay
from mozapkpublisher import upload_review_replies


credentials = NamedTemporaryFile()
upload_review_replies.MAX_BULK_SIZE = 1

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
VALID_CONFIG = {
    'package_name': 'org.mozilla.firefox_beta',
    'service-account': 'foo@developer.gserviceaccount.com',
    'credentials': credentials.name,
}


@pytest.fixture
def review_service_mock(monkeypatch):
    review_service_mock = create_autospec(googleplay.ReviewService)

    def rs(*args, **kwargs):
        return review_service_mock

    monkeypatch.setattr(googleplay, 'ReviewService', rs)
    return review_service_mock


def test_upload_review_replies(review_service_mock, monkeypatch):

    config = copy(VALID_CONFIG)
    config['replies'] = os.path.join(DATA_DIR, 'replies.csv')
    config['contact_google_play'] = False
    upload_review_replies.UploadReviewReplies(config).run()

    review_service_mock.reply.assert_called()


def test_upload_review_replies_with_all_flags(review_service_mock, monkeypatch, tmpdir):

    config = copy(VALID_CONFIG)
    config['replies'] = os.path.join(DATA_DIR, 'replies.csv')
    config['contact_google_play'] = False
    config['id_blacklist'] = os.path.join(DATA_DIR, 'review_blacklist.txt')
    config['id_log'] = os.path.join(tmpdir, "id_log.txt")
    upload_review_replies.UploadReviewReplies(config).run()

    review_service_mock.reply.assert_called_once()


def test_main(monkeypatch):
    incomplete_args = [
        '--package-name', 'org.mozilla.firefox_beta',
        '--service-account', 'foo@developer.gserviceaccount.com',
    ]

    monkeypatch.setattr(sys, 'argv', incomplete_args)

    with pytest.raises(SystemExit):
        upload_review_replies.main()
