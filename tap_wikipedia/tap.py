"""wikipedia tap class."""

from __future__ import annotations

from typing import List, Dict

from singer_sdk import Tap
from singer_sdk import typing as th

from tap_wikipedia.wikipedia_streams import WikipediaStream


class Tapwikipedia(Tap):
    """wikipedia tap class."""

    name = "tap-wikipedia"

    config_jsonschema = th.PropertiesList(
        th.Property("settings",
                    th.ObjectType(
                        th.Property("abstracts-dump-url", th.StringType),
                        th.Property("cache-path", th.StringType),
                        th.Property("subset-specification",
                                    th.ArrayType(th.StringType))
                    ),
                    ),
    ).to_dict()

    def get_config(self) -> Dict | None:
        """Return the contents of Tap configuration

        Returns:
            A dict of configuration values for tap-wikipedia, or None if the config file is empty. 
        """
        return self.config.get("settings", None)

    def discover_streams(self) -> List[WikipediaStream]:
        """Return a list of discovered streams.

        Returns:
            A list of discovered streams.
        """
        return [
            WikipediaStream(tap=self,
                            wikipedia_config=self.get_config())
        ]


if __name__ == "__main__":
    Tapwikipedia.cli()
