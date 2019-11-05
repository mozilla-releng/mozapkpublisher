# MozApkPublisher

Scripts to publish Firefox for Android on Google Play Store.

## Setup and run

1. :warning: You need Python >= 3.6 to run this set of scripts. Python 2 isn't supported starting version 0.5.0. Python 3.5 was removed in version 3.0.0.
1. Create a virtualenv and source it
```sh
virtualenv -p python3 venv
source venv/bin/activate
```
1. `pip install -r requirements.txt`
1. `python setup.py develop`
1. You can now execute the scripts in the `mozapkpublisher/` subfolder.
    * Note that some of the scripts either need to have [credentials](#run-push_apkpy-against-a-real-app-store) or to be flagged to not actually contact a real server 
1. Run `--help` to each of these script to know how to call them.

### Setup in Mac OSX


1. Install Xcode command line tools
   `xcode-select --install`
1. Create a virtualenv and source it
1. `pip install -r requirements.txt`
1. Some errors might happen during `python setup.py develop`
    1. fatal error: 'openssl/opensslv.h' file not found
        1. Temporarily adjust permissions on /usr/local so brew can update:
            * `sudo chgrp -R admin /usr/local`
            * `sudo chmod -R g+w /usr/local`
        2. Install the updated version of OpenSSL (you probably use 1.0.2j):
            * `brew install openssl`
        3. You may want/need to delete an existing symlink to openssl from /usr/local/bin:
            * `rm /usr/local/bin/openssl`
        4. Re-link the proper brew version:
            * `sudo ln -s /usr/local/Cellar/openssl/1.0.2i/bin/openssl /usr/local/bin/openssl`
            * `sudo ln -s /usr/local/Cellar/openssl/1.0.2j/include/openssl/ /usr/local/include/openssl`
        5. Restore original permissions on /usr/local/bin:
            * `sudo chown root:wheel /usr/local`
1. Some errors might happen when executing `mozapkpublisher/push_apk.py`
    1. You might have errors like
        * Errors in from_p12_keyfile in oauth2client/service_account.py or
        * ImportError: cannot import name `_openssl_crypt`
            * `pip uninstall oauth2client`
            * `pip install oauth2client==2.0.0`
            * `pip install google-api-python-client==1.5.0`
    1. Symbol not found: `_BIO_new_CMS`
        * `pip uninstall cryptography`
        * `LDFLAGS="-L/usr/local/opt/openssl/lib" pip install cryptography --no-use-wheel`
        
## Run `push_apk.py` against a real app store

For both Google and Amazon, we have an "Automation Test" app in our own indepent "Staging Releng" organization.
You can test `push_apk.py` integration against the real app stores by having it release an app update for this "Automation Test" app.

### Targeting Google Play

1. You'll need `mozapkpublisher` to authorize itself as a service account. To get credentials for the service account:
    1. Go to the [Google Cloud Platform Console](https://console.cloud.google.com/)
    1. In the top-right, sign in as "Mozilla Staging" (credentials are in the releng private repository)
    1. In the top-left, select the project with id `api-8823958359720455089-574384`
    1. Go to "IAM and admin" in the left navigation bar
    1. Go to "Service accounts"
    1. Click the service account whose email is `mozapkpublisher@api-8823958359720455089-574384.iam.gserviceaccount.com`
    1. Click "EDIT" in the top
    1. Click "CREATE KEY"
    1. Choose the `P12` key type
    1. Save the key and remember where you put it
1. You need to generate a new version of the dummy automation test app
    1. When uploading new versions of the app, they must have a larger android `versionCode` than the previous version. 
    You need to find out the current version so you can set a larger one.
        1. Go to the [Google Developer Console](https://play.google.com/apps/publish/)
        1. In the top-right, change your account to "Mozilla Releng Staging"
        1. Choose the "Mozilla Automation Test" app
        1. On the left navigation panel, go to "Release management" > "Artifact library"
        1. Find the highest "Version code"
    1. Build the app with a version code one higher than the highest in Google Play
        1. If you don't have a [keystore](https://developer.android.com/studio/publish/app-signing#certificates-keystores) already, you should create one
        1. Open a terminal in `app/`
        1. `./build.sh $VERSION_CODE $PATH_TO_KEYSTORE`
            * e.g.: `./build.sh 1 ~/keystore.jks`
            * The compiled, signed app will be at `app/build/outputs/apk/release/app-release.apk`
1. Finally, run `push_apk.py`

```
push_apk.py --expected-package-name=org.mozilla.automationtest \
    --skip-checks-fennec \
    --skip-check-same-locales \
    --skip-check-multiple-locales \
    --skip-check-ordered-version-codes \
    --username mozapkpublisher@api-8823958359720455089-574384.iam.gserviceaccount.com \
    --secret /path/to/p12/file/you/downloaded \
    google \
    internal \
    app/build/outputs/apk/release/app-release.apk
```

### Targeting Amazon

1. You'll need `mozapkpublisher` to authorize itself as a security profile. The security profile credentials are in the releng private repository
1. You need to generate a new version of the dummy automation test app
    1. When uploading new versions of the app, they must have a larger android `versionCode` than the previous version. 
    You need to find out the current version so you can set a larger one.
        1. Go to the [Amazon Developer Console](https://developer.amazon.com/)
        1. In the top-right, sign in
        1. Go to Apps & Services
        1. Click on Mozilla Automation Test
        1. Go to the APK Files tab and look for the "Ver Code"
    1. Build the app with a version code one higher than the highest in Amazon
        1. If you don't have a [keystore](https://developer.android.com/studio/publish/app-signing#certificates-keystores) already, you should create one
        1. Open a terminal in `app/`
        1. `./build.sh $VERSION_CODE $PATH_TO_KEYSTORE`
            * e.g.: `./build.sh 1 ~/keystore.jks`
            * The compiled, signed app will be at `app/build/outputs/apk/release/app-release.apk`
1. Finally, run `push_apk.py`

```
push_apk.py --expected-package-name=org.mozilla.automationtest \
    --skip-checks-fennec \
    --skip-check-same-locales \
    --skip-check-multiple-locales \
    --skip-check-ordered-version-codes \
    --username AMZN_CLIENT_ID \
    --secret AMZN_CLIENT_SECRET \
    amazon \
    app/build/outputs/apk/release/app-release.apk
```