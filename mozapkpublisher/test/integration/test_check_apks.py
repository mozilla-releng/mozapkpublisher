import os
import sys

from mozapkpublisher.check_apks import main

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')


def test_check_apks(monkeypatch):
    monkeypatch.setattr(sys, 'argv', [
        'irrelevant_string',
        '--expected-package-name', 'org.mozilla.firefox',
        os.path.join(DATA_DIR, 'fennec-x86.apk'),
        os.path.join(DATA_DIR, 'fennec-arm.apk'),
    ])
    main()
