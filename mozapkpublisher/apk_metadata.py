from xml.dom import minidom
from zipfile import ZipFile

from axmlparserpy.axmlprinter import AXMLPrinter


# Even though a class called APK exists in axmlparserpy, it's not compatible with Python 3 (unlike the rest of the
# library). That's why a simpler version is defined here
def extract_metadata_from_apk(file_name):
    with ZipFile(file_name) as apk_file:
        with apk_file.open('AndroidManifest.xml') as manifest_file:
            manifest_binary_content = manifest_file.read()

    manifest_string_content = AXMLPrinter(manifest_binary_content).getBuff()
    xml_manifest = minidom.parseString(manifest_string_content)

    return {
        # Google Play uses integers
        'version_code': int(xml_manifest.documentElement.getAttribute('android:versionCode')),
    }
