#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: ./build.sh VERSION KEYSTORE_LOCATION"
    echo "Example: ./build.sh 1 ~/keystore.jks"
    exit 1
fi

if ! compgen -G "$ANDROID_HOME/build-tools/*" > /dev/null; then
    echo 'Android build tools could not be located at $ANDROID_HOME/build-tools/'
    exit 2
fi

version_code=$1
keystore_path=$2

build_tools_options=($ANDROID_HOME/build-tools/*)
build_tools=${build_tools_options[-1]}
echo $build_tools

./gradlew assembleRelease -PversionCode=$version_code
$build_tools/zipalign -v -p 4 build/outputs/apk/release/app-release-unsigned.apk build/outputs/apk/release/app-release-unsigned-aligned.apk
$build_tools/apksigner sign --ks $keystore_path --out build/outputs/apk/release/app-release.apk build/outputs/apk/release/app-release-unsigned-aligned.apk