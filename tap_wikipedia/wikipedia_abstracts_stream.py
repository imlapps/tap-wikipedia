from __future__ import annotations

from pathlib import Path

from requests_cache import CachedSession


import xml.sax as sax
from bs4 import BeautifulSoup


import logging
import json


from typing import Tuple, Iterable, Dict

from singer_sdk import Tap

from tap_wikipedia.models import wikipedia, Config, WIKIPEDIA_TITLE_PREFIX
from tap_wikipedia.models.types import (
    EnrichmentType,
    SubsetSpecification,
    Title,
    ImageUrl,
    WebPageUrl,
)
from tap_wikipedia.wikipedia_stream import WikipediaStream
from tap_wikipedia.utils import FileCache, WikipediaAbstractsParser, pipe


class WikipediaAbstractsStream(WikipediaStream):
    """
        A concrete implementation of Wikipedia Stream.

        Extract abstracts dumps from the Wikimedia Foundation project (`dumps.wikimedia.org`),

        parse the abstracts into records, and yield them.
    """

    def __init__(self, tap: Tap, wikipedia_config: Config):
        super().__init__(
            tap=tap, name="abstracts", schema=wikipedia.Record.model_json_schema()
        )
        self.wikipedia_config = wikipedia_config
        self.__session = CachedSession(
            "tap_wikipedia_cache", expire_after=3600)
        self.__logger = logging.getLogger(__name__)

    def __get_featured_articles(self) -> tuple[WebPageUrl, ...]:
        """Retrieve URLs of featured Wikipedia articles."""

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

    def __get_wikipedia_records(
        self, cached_file_path: Path
    ) -> Iterable[wikipedia.Record]:
        """Parse Wikipedia abstracts and return a tuple of Wikipedia records."""

        # Setup parser
        parser = sax.make_parser()
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        handler = WikipediaAbstractsParser()
        parser.setContentHandler(handler)
        parser.parse(cached_file_path)

        return handler.records

    def __get_wikipedia_record_categories(
        self, wikipedia_article_url: WebPageUrl
    ) -> tuple[wikipedia.Category, ...]:
        """Return a tuple of a Wikipedia article's categories."""

        return (
            wikipedia.Category(
                text=category_item.get("href"), link=category_item.text.strip()
            )
            for category_item in BeautifulSoup(
                self.__session.get(wikipedia_article_url).text, "html.parser"
            )
            .find("a", {"title": "Help:Category"})
            .find_next_sibling()
            .findAll("a")
        )

    def __get_wikipedia_record_external_links(
        self, wikipedia_title: Title
    ) -> tuple[wikipedia.ExternalLink, ...]:  # noqa: E501
        """Return a tuple of external Wikipedia article links on a Wikipedia article."""

        # Clean Wikipedia title
        if wikipedia_title.startswith(WIKIPEDIA_TITLE_PREFIX):
            wikipedia_title = wikipedia_title[len(
                WIKIPEDIA_TITLE_PREFIX):].strip()

        response = self.__session.get(
            url="https://en.wikipedia.org/w/api.php",
            params={
                "action": "parse",
                "page": wikipedia_title,
                "format": "json",
            },
        )

        external_links = tuple(
            wikipedia.ExternalLink(
                title=wikipedia_json["*"].title(),
                link="https://en.wikipedia.org/wiki/"
                + wikipedia_json["*"].replace(" ", "_"),
            )
            for wikipedia_json in response.json()["parse"]["links"]
            if wikipedia_json["ns"] == 0
        )

        return external_links

    def __get_wikipedia_record_image_url(
        self, wikipedia_article_url: WebPageUrl
    ) -> ImageUrl | None:
        """Retrieve the ImageURL of a Wikipedia record."""

        img_url = None
        soup = BeautifulSoup(
            self.__session.get(wikipedia_article_url).text, "html.parser"
        )

        file_description_url = soup.find("a", {"class": "mw-file-description"})["href"][
            6:
        ]  # noqa: E501

        # Get a better resolution of the Wikipedia image
        minimum_image_width = 500
        if file_description_url is not None:
            img_url = self.__select_wikipedia_image_resolution(
                file_description_url, minimum_image_width
            )

        # If no better resolution is found, use existing image url on Wikipedia page
        if img_url == None:
            img_url = (
                soup.find("a", {"class": "mw-file-description"})
                .findChild()
                .get("src", None)
            )

        return img_url

    def __select_wikipedia_image_resolution(
        self, file_description_url: WebPageUrl, minimum_image_width: int
    ) -> ImageUrl | None:
        """
            Retrieve the ImageURL of a high-quality image from Wikimedia Commons API.

            `minimum_image_width` is used as a guide to select the best image from the API.
        """

        base_url = "https://api.wikimedia.org/core/v1/commons/file/"
        url = base_url + file_description_url

        response = dict(json.loads(
            self.__session.get(url, headers={"User-agent": "Imlapps"}).text
        ))

        display_title = response.get("title", "")
        selected_file_url = None

        try:
            # Select an image in increasing order of preference.
            if ("preferred" in response) and (
                response["preferred"].get("width", 0) >= minimum_image_width
            ):
                selected_file_url = response["preferred"].get("url", None)
            elif "original" in response:
                selected_file_url = response["original"].get("url", None)
            elif "thumbnail" in response:
                selected_file_url = response["thumbnail"].get("url", None)

            # If no image is selected, settle for an image with a width less than the minimum_image_width
            if selected_file_url == None:
                if ("preferred" in response) and response["preferred"].get("url") != "":
                    selected_file_url = response["preferred"].get("url")

        except Exception:
            self.__logger.warning(
                f"Error while selecting an image URL file for {display_title} from Wikimedia Commons.",  # noqa: E501
                exc_info=True,
            )
        return selected_file_url

    def get_records(self, context: Dict | None) -> Iterable[Dict]:
        """Generate a stream of Wikipedia records"""

        try:
            cached_file_path = FileCache(
                cache_dir_path=self.wikipedia_config.cache_directory_path
            ).get_file(self.wikipedia_config.abstracts_dump_url)
        except Exception:
            self.__logger.warning(
                f"Error while downloading Wikipedia dump from {self.wikipedia_config.abstracts_dump_url}",
                exc_info=True,
            )  # noqa: E501
            return 1

        def add_categories_to_records(
            records: Iterable[wikipedia.Record],
        ) -> Iterable[wikipedia.Record]:
            """Enrich Wikipedia records with their categories and yield the records."""

            for record in records:
                try:
                    categories = self.__get_wikipedia_record_categories(
                        record.abstract_info.url
                    )
                except Exception:
                    self.__logger.warning(
                        f"Error while getting the categories of Wikipedia article: {record.abstract_info.title}",  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.categories = categories
                yield record

        def add_external_links_to_records(
            records: Iterable[wikipedia.Record],
        ) -> Iterable[wikipedia.Record]:
            """Enrich Wikipedia records with their external links and yield the records."""

            for record in records:
                try:
                    external_links = (
                        self.__get_wikipedia_record_external_links(  # noqa: E501
                            record.abstract_info.title
                        )
                    )
                except Exception:
                    self.__logger.warning(
                        f"Error while getting the external links of Wikipedia article: {record.abstract_info.title}",  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.external_links = external_links
                yield record

        def add_image_url_to_records(
            records: Iterable[wikipedia.Record],
        ) -> Iterable[wikipedia.Record]:
            """Enrich Wikipedia records with their ImageURLs and yield the records."""

            for record in records:
                try:
                    img_url = self.__get_wikipedia_record_image_url(
                        record.abstract_info.url
                    )
                except Exception:
                    self.__logger.warning(
                        f"Error while getting the image URL of Wikipedia article: {record.abstract_info.title}",  # noqa: E501
                        exc_info=True,
                    )
                    continue

                record.abstract_info.imageUrl = img_url
                yield record

        def get_featured_records(
            records: Iterable[wikipedia.Record],
        ) -> Iterable[wikipedia.Record]:
            """Retrieve a list of featured Wikipedia article URLs and yield records that match the URLs."""

            featured_urls = self.__get_featured_articles()

            for record in records:
                if record.abstract_info.url in featured_urls:
                    yield record

        records = self.__get_wikipedia_records(cached_file_path)
        pipe_callables = []

        for specification in self.wikipedia_config.subset_specifications:
            if specification == SubsetSpecification.FEATURED:
                pipe_callables.append(get_featured_records(records))
                # records = get_featured_records(records)

        for enrichment in self.wikipedia_config.enrichments:
            if enrichment == EnrichmentType.IMAGE_URL:
                pipe_callables.append(add_image_url_to_records(records))
                # records = add_image_url_to_records(records)

            if enrichment == EnrichmentType.CATEGORY:
                pipe_callables.append(add_categories_to_records(records))
                # records = add_categories_to_records(records)

            if enrichment == EnrichmentType.EXTERNAL_LINK:
                pipe_callables.append(
                    add_external_links_to_records(records))
                # records = add_external_links_to_records(records)

        yield from pipe(pipe_callables=pipe_callables, initializer=records)
