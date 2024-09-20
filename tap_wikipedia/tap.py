"""wikipedia tap class."""

from __future__ import annotations

from typing import TYPE_CHECKING

from singer_sdk import Tap

from tap_wikipedia.models import Config
from tap_wikipedia.wikipedia_abstracts_stream import WikipediaAbstractsStream

if TYPE_CHECKING:
    from tap_wikipedia.wikipedia_stream import WikipediaStream


class TapWikipedia(Tap):
    """Singer Tap for Wikipedia data."""

    name = "tap-wikipedia"

    config_jsonschema = Config.model_json_schema()

    def get_config(self) -> Config:
        """Return the contents of Tap configuration

        Returns:
            A dict of configuration values for tap-wikipedia,
            or None if the config file is empty.
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
