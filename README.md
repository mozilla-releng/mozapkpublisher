# MozApkPublisher

Scripts to publish Firefox for Android on Google Play Store.

## Run

1. Create a virtualenv and source it
1. `python setup.py develop`
1. Execute either `mozapkpublisher/get_apk.py`, or `mozapkpublisher/push_apk.py`, or `mozapkpublisher/update_apk_description.py`
1. Run `--help` to each of these script to know how to call them.

#### Setup in Mac OSX


1. Install Xcode command line tools
   `xcode-select --install`
1. Create a virtualenv and source it
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
        * ImportError: cannot import name _openssl_crypt  
            * `pip uninstall oauth2client`  
            * `pip install oauth2client==2.0.0`  
            * `pip install google-api-python-client==1.5.0`  
    1. Symbol not found: _BIO_new_CMS  
        * `pip uninstall cryptography`  
        * `LDFLAGS="-L/usr/local/opt/openssl/lib" pip install cryptography --no-use-wheel`  