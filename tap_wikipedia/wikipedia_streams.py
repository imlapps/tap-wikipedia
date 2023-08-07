from __future__ import annotations

import requests
import xml.sax as sax
from bs4 import BeautifulSoup
from urllib.parse import urlparse

import logging
from appdirs import *
from pathlib import Path
from typing import Tuple, Iterable, List, Dict, Any

import singer_sdk.typing as th
from singer_sdk import Stream, Tap

from tap_wikipedia.utils.file_cache import FileCache
from tap_wikipedia.utils.wikipedia_abstracts_parser import WikipediaAbstractsParser


class WikipediaStream(Stream):
    """Stream class for wikipedia streams."""

    def __init__(self, tap: Tap, wikipedia_config: dict | None):
        super().__init__(
            tap=tap,
            name="abstracts",
            schema=th.PropertiesList(
                th.Property("info",
                            th.ObjectType(th.Property("title", th.StringType),
                                          th.Property(
                                "abstract", th.StringType),
                                th.Property(
                                "url", th.StringType),
                            ),
                            ),

                th.Property("sublinks",
                            th.ArrayType(
                                th.ObjectType(
                                    th.Property("anchor", th.StringType),
                                    th.Property("link", th.StringType)
                                )
                            ),
                            )
            ).to_dict(),
        )
        self.__logger = logging.getLogger(__name__)
        self.wikipedia_config = wikipedia_config

    def __get_featured_articles(self) -> List[str]:
        """Retrieve URLs of Featured Wikipedia Articles"""

        url = "https://en.wikipedia.org/wiki/Wikipedia:Featured_articles"
        links = []

        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all('a'):
            current_link = str(link.get('href'))
            if current_link[:5] == "/wiki":
                links.append(current_link)

        featured_urls = list("https://en.wikipedia.org" +
                             link for link in links)

        return featured_urls

    def __get_wikipedia_records(self, cached_file_path) -> List[Any]:
        """Retrieve list of Wikipedia Records"""

        # Setup parser
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        Handler = WikipediaAbstractsParser()
        parser.setContentHandler(Handler)
        parser.parse(cached_file_path)

        # Return list of records
        return Handler.getRecords()

    def get_records(
        self,
        context: Dict | None
    ) -> Iterable[Dict]:
        """Generate Stream of Wikipedia Records"""

        # Set default config values
        default_url = 'https://dumps.wikimedia.org/enwiki/latest/enwiki-latest-abstract1.xml.gz'
        default_cache_dir = user_cache_dir("abstracts", "tap-wikipedia")

        # Get config values
        url = self.wikipedia_config.get("abstracts-dump-url", default_url)
        cache_dir = Path(self.wikipedia_config.get(
            "cache-path", default_cache_dir))
        subset_specification = self.wikipedia_config.get(
            "subset-specification", [])

        # Get cache directory
        abstractsCache = FileCache(cache_dir_path=cache_dir)
        try:
            cached_file_path = abstractsCache.get_file(url)
        except:
            self.__logger.warning(
                "error downloading Wikipedia dump", exc_info=True)
            return 1

        # get Wikipedia records
        records = self.__get_wikipedia_records(cached_file_path)

        # returns a list of featured Wikipedia Article records
        def get_featured_records() -> List[Any]:
            featured_urls = self.__get_featured_articles()

            filtered_records = [
                record for record in records if record["info"]["url"] in featured_urls]

            return filtered_records

        # Filter out featured Wikipedia Article records
        if "featured" in subset_specification:
            records = get_featured_records()

        for record in records:
            yield record
