import json
import pytest
import tempfile

from mozapkpublisher.get_l10n_strings import GetL10nStrings
from mozapkpublisher.common.store_l10n import STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME, check_translations_schema
from mozapkpublisher.test import skip_when_no_network


@skip_when_no_network
@pytest.mark.parametrize('package_name', STORE_PRODUCT_DETAILS_PER_PACKAGE_NAME.keys())
def test_download_files(package_name):
    with tempfile.NamedTemporaryFile('w+t', encoding='utf-8') as f:
        config = {
            'package_name': package_name,
            'output_file': f.name,
        }
        GetL10nStrings(config).run()

        f.seek(0)
        data = json.load(f)
        # In reality, this call is already done by GetL10nStrings, but better safe than sorry
        check_translations_schema(data)
