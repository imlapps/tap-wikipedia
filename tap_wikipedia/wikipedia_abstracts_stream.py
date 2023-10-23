from __future__ import annotations

from requests_cache import CachedSession

import requests
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
                    "abstract_info",
                    th.ObjectType(
                        th.Property("title", th.StringType),
                        th.Property("abstract", th.StringType),
                        th.Property("url", th.StringType),
                        th.Property("image", th.StringType),
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
                th.Property(
                    "categories",
                    th.ArrayType(
                        th.ObjectType(
                            th.Property("text", th.StringType),
                            th.Property("link", th.StringType),
                        )
                    ),
                ),
                th.Property(
                    "externallinks",
                    th.ArrayType(
                        th.ObjectType(
                            th.Property("title", th.StringType),
                            th.Property("link", th.StringType),
                        )
                    ),
                ),
            ).to_dict(),
        )
        self.wikipedia_config = wikipedia_config
        self.__logger = logging.getLogger(__name__)

    def __get_wikipedia_record_images(self, url: str) -> str:
        """Retrieve URL of a single wikipedia record"""

        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        img_url = ""

        img_url = (
            soup.find("a", {"class": "mw-file-description"}).findChild().get("src")  # type: ignore # noqa: E501
        )
        if img_url is None:
            img_url = ""

        return img_url

    def __get_wikipedia_record_categories(self, url: str) -> Tuple[Dict, ...]:
        """Retrieve URL of a single wikipedia record"""

        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        categories = []

        unordered_category_list = soup.find("a", {"title": "Help:Category"}).find_next_sibling().findAll("a")  # type: ignore # noqa: E501

        for list_item in unordered_category_list:
            category_link = list_item.get("href")
            category_text = list_item.text.strip()
            categories.append({"text": category_text, "link": category_link})

        return tuple(categories)

    def __get_wikipedia_record_external_links(
        self, title: str
    ) -> Tuple[Dict, ...]:  # noqa: E501
        """Retrieve external Wikipedia links from a Wikipedia article"""

        # Clean Wikipedia title
        if title[:10] == "Wikipedia:":
            title = title[10:].strip()

        media_wiki_url = "https://en.wikipedia.org/w/api.php"
        media_wiki_params = {
            "action": "parse",
            "page": title,
            "format": "json",
        }  # noqa: E501

        response = requests.get(url=media_wiki_url, params=media_wiki_params)

        external_links_titles = filter(
            lambda wikipedia_json: wikipedia_json["ns"] == 0,
            response.json()["parse"]["links"],
        )

        external_links = tuple(
            {
                "title": wikipedia_json["*"].title(),
                "link": "https://en.wikipedia.org/wiki/"
                + wikipedia_json["*"].replace(" ", "_"),
            }
            for wikipedia_json in external_links_titles
        )

        return external_links

    def __get_featured_articles(self) -> Tuple[str, ...]:
        """Retrieve URLs of Featured Wikipedia articles"""

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

    def __get_wikipedia_records(self, cached_file_path) -> Iterable[Dict]:
        """Retrieve list of Wikipedia Records"""

        # Setup parser
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        handler = WikipediaAbstractsParser()
        parser.setContentHandler(handler)
        parser.parse(cached_file_path)

        # Return tuple of records
        return handler.records

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
        enhancements = self.wikipedia_config.get("enhancements", [])
        clean_entries = self.wikipedia_config.get("clean-entries", [])

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

        # generates a stream of featured Wikipedia article records
        def get_featured_records(records) -> Iterable[Dict]:
            featured_urls = self.__get_featured_articles()

            for record in records:
                if record["abstract_info"]["url"] in featured_urls:
                    yield record

        # adds the main image of the Wikipedia article to the Wikipedia record
        def add_images_to_records(records) -> Iterable[Dict]:
            for record in records:
                try:
                    img_url = self.__get_wikipedia_record_images(
                        record["abstract_info"]["url"]
                    )
                except Exception:
                    self.__logger.warning(
                        f'error getting URL of {record["abstract_info"]["title"]}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record["abstract_info"]["image"] = img_url
                yield record

        # adds a list of categories to the Wikipedia record
        def add_categories_to_records(records) -> Iterable[Dict]:
            for record in records:
                try:
                    categories = self.__get_wikipedia_record_categories(
                        record["abstract_info"]["url"]
                    )
                except Exception:
                    self.__logger.warning(
                        f'error getting category of {record["abstract_info"]["title"]}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record["categories"] = categories
                yield record

        # adds a list of external links to the Wikipedia record
        def add_external_links_to_records(records):
            for record in records:
                try:
                    external_links = (
                        self.__get_wikipedia_record_external_links(  # noqa: E501
                            record["abstract_info"]["title"]
                        )
                    )
                except Exception:
                    self.__logger.warning(
                        f'error getting external links of {record["abstract_info"]["title"]}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record["externallinks"] = external_links
                yield record

        # removes unwanted information from the title of  Wikipedia records
        def clean_wikipedia_titles(records) -> Iterable[Dict]:
            for record in records:
                # removes "Wikipedia" from the Wikipedia Title
                if record["abstract_info"]["title"][:10] == "Wikipedia:":
                    record["abstract_info"]["title"] = record["abstract_info"][
                        "title"
                    ][  # noqa: E501
                        10:
                    ].strip()

                yield record

        # removes unwanted information from the abstract of a Wikipedia record
        def clean_wikipedia_abstracts(records) -> Iterable[Dict]:
            for record in records:
                yield record

        for specification in subset_specification:
            # extract featured Wikipedia Article records
            if specification == "featured":
                records = get_featured_records(records)

        for enhancement in enhancements:
            # add images to Wikipedia Article records
            if enhancement == "images":
                records = add_images_to_records(records)

            # add categories to Wikipedia Article records
            if enhancement == "categories":
                records = add_categories_to_records(records)

            # add external links to Wikipedia Article records
            if enhancement == "externallinks":
                records = add_external_links_to_records(records)

        for entry in clean_entries:
            # remove irrelevant information from Wikipedia Title
            if entry == "title":
                records = clean_wikipedia_titles(records)

            # remove non-alphanumeric characters from Wikipedia Abstract
            # if entry == "abstract":
            #     records = clean_wikipedia_abstracts(records)

        yield from records
