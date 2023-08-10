from __future__ import annotations


from requests_cache import CachedSession

import xml.sax as sax
from bs4 import BeautifulSoup


import logging
from appdirs import user_cache_dir
from pathlib import Path
from typing import Tuple, Iterable, Dict

import singer_sdk.typing as th
from singer_sdk import Tap
from tap_wikipedia.wikipedia_stream import WikipediaStream

from tap_wikipedia.utils.file_cache import FileCache
from tap_wikipedia.utils.wikipedia_abstracts_parser import (
    WikipediaAbstractsParser,
)  # noqa: E501


class WikipediaAbstractsStream(WikipediaStream):
    """A concrete implementation of the Wikipedia Stream class."""

    def __init__(self, tap: Tap, wikipedia_config: Dict):
        super().__init__(
            tap=tap,
            name="abstracts",
            schema=th.PropertiesList(
                th.Property(
                    "info",
                    th.ObjectType(
                        th.Property("title", th.StringType),
                        th.Property("abstract", th.StringType),
                        th.Property("url", th.StringType),
                    ),
                ),
                th.Property(
                    "sublinks",
                    th.ArrayType(
                        th.ObjectType(
                            th.Property("anchor", th.StringType),
                            th.Property("link", th.StringType),
                        )
                    ),
                ),
            ).to_dict(),
        )
        self.wikipedia_config = wikipedia_config
        self.__logger = logging.getLogger(__name__)

    def __get_featured_articles(self) -> Tuple[str, ...]:
        """Retrieve URLs of Featured Wikipedia Articles"""

        session = CachedSession("featured_articles_cache", expire_after=3600)

        url = "https://en.wikipedia.org/wiki/Wikipedia:Featured_articles"
        links = []

        response = session.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("a"):
            current_link = str(link.get("href"))
            if current_link[:5] == "/wiki":
                links.append(current_link)

        links.sort()
        featured_urls = tuple(
            "https://en.wikipedia.org" + link for link in links  # noqa: E501
        )

        return featured_urls

    def __get_wikipedia_records(self, cached_file_path) -> Tuple[Dict, ...]:
        """Retrieve list of Wikipedia Records"""

        # Setup parser
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        Handler = WikipediaAbstractsParser()
        parser.setContentHandler(Handler)
        parser.parse(cached_file_path)

        # Return tuple of records
        return Handler.records

    def get_records(self, context: Dict | None) -> Iterable[Dict]:
        """Generate Stream of Wikipedia Records"""

        # Set default config values
        default_url = "https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract1.xml.gz"  # noqa: E501
        default_cache_dir = user_cache_dir("abstracts", "tap-wikipedia")

        # Get config values
        url = self.wikipedia_config.get("abstracts-dump-url", default_url)
        cache_dir = Path(
            self.wikipedia_config.get("cache-path", default_cache_dir)  # noqa: E501
        )
        subset_specification = self.wikipedia_config.get("subset-spec", [])

        # Get cache directory
        abstractsCache = FileCache(cache_dir_path=cache_dir)
        try:
            cached_file_path = abstractsCache.get_file(url)
        except Exception:
            self.__logger.warning(
                "error downloading Wikipedia dump", exc_info=True
            )  # noqa: E501
            return 1

        # get Wikipedia records
        records = self.__get_wikipedia_records(cached_file_path)

        # returns a list of featured Wikipedia Article records
        def get_featured_records() -> Iterable[Dict]:
            featured_urls = self.__get_featured_articles()

            for record in records:
                if record["info"]["url"] in featured_urls:
                    yield record

        # Filter out featured Wikipedia Article records
        if "featured" in subset_specification:
            yield from get_featured_records()
        else:
            yield from records
