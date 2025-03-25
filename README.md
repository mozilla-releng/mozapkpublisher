# MozApkPublisher

Scripts to publish Firefox for Android on Google Play Store.

## Setup and run

1. :warning: You need Python >= 3.6 to run this set of scripts. Python 2 isn't supported starting version 0.5.0. Python 3.5 was removed in version 3.0.0.
1. `uv venv`
1. `uv pip install -e .`
1. If using push_aab.py, download `bundletool` from https://github.com/google/bundletool/releases and set environment variable `BUNDLETOOL_PATH=path/to/bundletool.jar`
1. Execute either `mozapkpublisher/push_apk.py`, or `mozapkpublisher/push_aab.py`, or `mozapkpublisher/update_apk_description.py`
1. Run `--help` to each of these script to know how to call them.

### Running tests

1. `uv tool install tox --with tox-uv`
1. `uv tool run tox -e py39`

### Preparing a release

1. `uv tool run hatch build`

## What to do when pushapk_scriptworker doesn't work?

> A guide to manually publish APKs onto Google Play Store

1. Generate a Google Play Store json certificate. This certificate needs to have write access to the app you want to publish. In this context, "app" means Fennec, Fennec Beta or Fennec Nightly.
1. Execute the steps defined in the section above.
1. Download the latest [signed builds](https://treeherder.mozilla.org/jobs?repo=mozilla-central&searchStr=signing-bundle-fenix-nightly)
1. 
```sh
uv run python ./mozapkpublisher/push_apk.py --no-gp-string-update --track beta --credentials /path/to/your/googleplay/creds.json x86.apk arm.apk
```

  * Note `beta` track on Google Play, that's our way to show to people on Play Store that it's not a finished product. We don't use the "production" track for Nightly, unlike beta and release.
1. If all goes well, add `--commit` to the command line and rerun it.
