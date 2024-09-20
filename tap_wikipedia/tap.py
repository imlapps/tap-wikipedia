"""wikipedia tap class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_wikipedia.models import Config
from tap_wikipedia.wikipedia_abstracts_stream import WikipediaAbstractsStream

if TYPE_CHECKING:
    from tap_wikipedia.wikipedia_stream import WikipediaStream


class TapWikipedia(Tap):
    """Singer Tap for Wikipedia data."""

    name = "tap-wikipedia"

    config_jsonschema = th.PropertiesList(
        th.Property(
            "settings",
            th.ObjectType(
                th.Property("abstracts-dump-url", th.StringType),
                th.Property("cache-directory-path", th.StringType),
                th.Property("clean-wikipedia-title", th.BooleanType),
                th.Property("enrichments", th.ArrayType(th.StringType)),
                th.Property("subset-specifications", th.ArrayType(th.StringType)),
            ),
        ),
    ).to_dict()

    def get_config(self) -> Config:
        """Return the contents of Tap configuration

        Returns:
            A Config object that contains configuration values for tap-wikipedia
        """

        return Config(**self.config.get("settings", {}))

    def discover_streams(self) -> list[WikipediaStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [WikipediaAbstractsStream(tap=self, wikipedia_config=self.get_config())]


if __name__ == "__main__":
    TapWikipedia.cli()
