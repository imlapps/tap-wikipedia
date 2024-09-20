"""Tests standard tap features using the built-in SDK tests library."""

import datetime

from singer_sdk.testing import get_tap_test_class

from tap_wikipedia.tap import Tapwikipedia

SAMPLE_CONFIG = {
    "settings": {
        "abstracts-dump-url": "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract1.xml.gz",
        "subset-specification": ["featured"],
    }
}


# Run standard built-in tap tests from the SDK:
TestTapwikipedia = get_tap_test_class(
    tap_class=Tapwikipedia,
    config=SAMPLE_CONFIG,
)


# TODO: Create additional tests as appropriate for your tap.
