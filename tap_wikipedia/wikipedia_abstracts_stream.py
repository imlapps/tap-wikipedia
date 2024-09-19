from __future__ import annotations
from pathlib import Path

from requests_cache import CachedSession

import requests
import xml.sax as sax
from bs4 import BeautifulSoup


import logging
import json
from appdirs import user_cache_dir

from urllib.parse import unquote
from typing import Tuple, Iterable, Dict

from singer_sdk import Tap

from tap_wikipedia.models import wikipedia, Config
from tap_wikipedia.models.types import EnrichmentType, SubsetSpecification, Title, ImageUrl, WebPageUrl
from tap_wikipedia.wikipedia_stream import WikipediaStream
from tap_wikipedia.utils.file_cache import FileCache
from tap_wikipedia.utils.wikipedia_abstracts_parser import (
    WikipediaAbstractsParser,
)  # noqa: E501


class WikipediaAbstractsStream(WikipediaStream):
    """A concrete implementation of the Wikipedia Stream class."""

    def __init__(self, tap: Tap, wikipedia_config: Config):
        super().__init__(
            tap=tap,
            name="abstracts",
            schema=wikipedia.Abstract.model_json_schema()
        )
        self.wikipedia_config = wikipedia_config
        self.__session = CachedSession(
            "tap_wikipedia_cache", expire_after=3600)
        self.__logger = logging.getLogger(__name__)

    def __select_wikipedia_image_resolution(self, file_description_url: WebPageUrl, width: int) -> ImageUrl | None:
        """Use the specified width to retrieve the imageUrl of a particular resolution"""

        base_url = 'https://api.wikimedia.org/core/v1/commons/file/'
        url = base_url + file_description_url

        response = json.loads(self.__session.get(
            url, headers={'User-agent': 'Imlapps'}).text)

        display_title = response.get('title', "")
        selected_file_url = None

        try:
            if ('preferred' in response) and (response['preferred'].get('width', 0) >= width):
                selected_file_url = response['preferred'].get('url', None)
            elif ('original' in response):
                selected_file_url = response['original'].get('url', None)
            elif ('thumbnail' in response):
                selected_file_url = response['thumbnail'].get('url', None)

            if selected_file_url == None:
                if ('preferred' in response) and response['preferred'].get('url') != '':
                    selected_file_url = response['preferred'].get('url')

        except Exception:
            self.__logger.warning(
                        f'Error while selecting an image URL file for {display_title} from Wikimedia Commons.',  # noqa: E501
                        exc_info=True,
                    )
        return selected_file_url

    def __get_wikipedia_record_image_url(self, url: WebPageUrl) -> str | None:
        """Retrieve image URL of a single wikipedia record"""

        soup = BeautifulSoup(self.__session.get(url).text, "html.parser")

        img_url = None

        file_description_url = soup.find("a", {"class": "mw-file-description"})["href"][6:]  # type: ignore # noqa: E501

        # Get a better resolution of the Wikipedia image
        if file_description_url is not None:
            img_url = self.__select_wikipedia_image_resolution(
                file_description_url, 500)

        # If no better resolution is found, use existing image url on Wikipedia page
        if img_url == None:
            img_url = soup.find(
                "a", {"class": "mw-file-description"}).findChild().get('src', None)

        return img_url

    def __get_wikipedia_record_categories(self, url: WebPageUrl) -> tuple[wikipedia.Category, ...]:
        """Retrieve categories of a single wikipedia record"""

        soup = BeautifulSoup(self.__session.get(url).text, "html.parser")

        categories = []

        unordered_category_list = soup.find("a", {"title": "Help:Category"}).find_next_sibling().findAll("a")  # type: ignore # noqa: E501

        for list_item in unordered_category_list:
            category_link = list_item.get("href")
            category_text = list_item.text.strip()
            categories.append(wikipedia.Category(
                text=category_text, link=category_link))

        return tuple(categories)

    def __get_wikipedia_record_external_links(
        self, wikipedia_title: Title
    ) -> Tuple[wikipedia.ExternalLink, ...]:  # noqa: E501
        """Retrieve external Wikipedia links from a Wikipedia article"""

        # Clean Wikipedia title
        if wikipedia_title[:10] == "Wikipedia:":
            wikipedia_title = wikipedia_title[10:].strip()

        media_wiki_url = "https://en.wikipedia.org/w/api.php"
        media_wiki_params = {
            "action": "parse",
            "page": wikipedia_title,
            "format": "json",
        }  # noqa: E501

        response = requests.get(url=media_wiki_url, params=media_wiki_params)

        external_links_titles = filter(
            lambda wikipedia_json: wikipedia_json["ns"] == 0,
            response.json()["parse"]["links"],
        )

        external_links = tuple(
            wikipedia.ExternalLink(title=wikipedia_json["*"].title(),
                                   link="https://en.wikipedia.org/wiki/"
                                   + wikipedia_json["*"].replace(" ", "_"))
            for wikipedia_json in external_links_titles
        )

        return external_links

    def __get_featured_articles(self) -> tuple[WebPageUrl, ...]:
        """Retrieve URLs of Featured Wikipedia articles"""

        url = "https://en.wikipedia.org/wiki/Wikipedia:Featured_articles"
        links = []

        soup = BeautifulSoup(self.__session.get(url).text, "html.parser")

        for link in soup.find_all("a"):
            current_link = str(link.get("href"))
            if current_link[:5] == "/wiki":
                links.append(current_link)

        links.sort()
        featured_urls = tuple(
            "https://en.wikipedia.org" + link for link in links  # noqa: E501
        )

        return featured_urls

    def __get_wikipedia_records(self, cached_file_path: Path) -> tuple[wikipedia.Abstract, ...]:
        """Retrieve list of Wikipedia Records"""

        # Setup parser
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        handler = WikipediaAbstractsParser()
        parser.setContentHandler(handler)
        parser.parse(cached_file_path)

        # Return tuple of records
        return (wikipedia.Abstract(**record) for record in handler.records)

    def get_records(self, context: Dict | None) -> Iterable[Dict]:
        """Generate Stream of Wikipedia Records"""

        try:
            cached_file_path = FileCache(
                cache_dir_path=self.wikipedia_config.cache_directory_path).get_file(
                self.wikipedia_config.abstracts_dump_url)
        except Exception:
            self.__logger.warning(
                f'Error while downloading Wikipedia dump from {self.wikipedia_config.abstracts_dump_url}', exc_info=True
            )  # noqa: E501
            return 1

        # get Wikipedia records
        records = self.__get_wikipedia_records(cached_file_path)

        # generates a stream of featured Wikipedia article records
        def get_featured_records(records: tuple[wikipedia.Abstract, ...]) -> Iterable[wikipedia.Abstract]:
            featured_urls = self.__get_featured_articles()

            for record in records:
                if record.abstract_info.url in featured_urls:
                    yield record

        # adds the image url of a Wikipedia article to the Wikipedia record
        def add_image_url_to_records(records: tuple[wikipedia.Abstract, ...]) -> Iterable[wikipedia.Abstract]:
            for record in records:
                try:
                    img_url = self.__get_wikipedia_record_image_url(
                        record.abstract_info.url
                    )
                except Exception:
                    self.__logger.warning(
                        f'Error while getting the image URL of Wikipedia article: {record.abstract_info.title}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.abstract_info.imageUrl = img_url
                yield record

        # adds a list of categories to the Wikipedia record
        def add_categories_to_records(records: tuple[wikipedia.Abstract, ...]) -> Iterable[wikipedia.Abstract]:
            for record in records:
                try:
                    categories = self.__get_wikipedia_record_categories(
                        record.abstract_info.url
                    )
                except Exception:
                    self.__logger.warning(
                        f'Error while getting the categories of Wikipedia article: {record.abstract_info.title}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.categories = categories
                yield record

        # adds a list of external links to the Wikipedia record
        def add_external_links_to_records(records: tuple[wikipedia.Abstract, ...]) -> Iterable[Dict]:
            for record in records:
                try:
                    external_links = (
                        self.__get_wikipedia_record_external_links(  # noqa: E501
                            record.abstract_info.title
                        )
                    )
                except Exception:
                    self.__logger.warning(
                        f'Error while getting the external links of Wikipedia article: {record.abstract_info.title}',  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.external_links = external_links
                yield record

        for specification in self.wikipedia_config.subset_specifications:

            if specification == SubsetSpecification.FEATURED:
                records = get_featured_records(records)

        for enrichment in self.wikipedia_config.enrichments:

            if enrichment == EnrichmentType.IMAGE_URL:
                records = add_image_url_to_records(records)

            if enrichment == EnrichmentType.CATEGORY:
                records = add_categories_to_records(records)

            if enrichment == EnrichmentType.EXTERNAL_LINK:
                records = add_external_links_to_records(records)

        yield from records
