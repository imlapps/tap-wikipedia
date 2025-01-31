from __future__ import annotations

import json
import logging
from functools import reduce
from typing import TYPE_CHECKING
from xml import sax

from bs4 import BeautifulSoup
from pydantic import AnyUrl
from requests import HTTPError
from requests_cache import CachedSession

from tap_wikipedia.constants import (
    WIKI_SUBDIRECTORY,
    WIKIPEDIA_TITLE_PREFIX,
    WikipediaUrl,
)
from tap_wikipedia.models import Config, wikipedia
from tap_wikipedia.models.types import EnrichmentType, NonBlankString
from tap_wikipedia.models.types import StrippedString as Title
from tap_wikipedia.models.types import SubsetSpecification
from tap_wikipedia.utils import FileCache, WikipediaAbstractsParser
from tap_wikipedia.wikipedia_stream import WikipediaStream

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from pathlib import Path

    from singer_sdk import Tap


class WikipediaAbstractsStream(WikipediaStream):
    """
    A concrete implementation of Wikipedia Stream.

    Extract an abstracts dump from the Wikimedia Foundation project (`dumps.wikimedia.org`),

    parse the abstracts, and yield them as records.
    """

    def __init__(self, tap: Tap, wikipedia_config: Config):
        super().__init__(
            tap=tap, name="abstracts", schema=wikipedia.Record.model_json_schema()
        )
        self.wikipedia_config = wikipedia_config
        self.__session = CachedSession("tap_wikipedia_cache")
        self.__logger = logging.getLogger(__name__)

    def __add_categories_to_records(
        self,
        records: Iterable[wikipedia.Record],
    ) -> Iterable[wikipedia.Record]:
        """Enrich Wikipedia records with their categories and yield the records."""

        for record in records:
            try:
                categories = self.__get_wikipedia_record_categories(
                    record.abstract_info.url
                )
            except HTTPError:
                self.__logger.warning(
                    f"Error while getting the categories of Wikipedia article: {record.abstract_info.title}",
                    exc_info=True,
                )
                continue

            record.categories = categories
            yield record

    def __add_external_links_to_records(
        self,
        records: Iterable[wikipedia.Record],
    ) -> Iterable[wikipedia.Record]:
        """Enrich Wikipedia records with their external links and yield the records."""

        for record in records:
            try:
                external_links = self.__get_wikipedia_record_external_links(
                    record.abstract_info.title
                )
            except HTTPError:
                self.__logger.warning(
                    f"Error while getting the external links of Wikipedia article: {record.abstract_info.title}",
                    exc_info=True,
                )
                continue

            record.external_links = external_links
            yield record

    def __add_image_url_to_records(
        self,
        records: Iterable[wikipedia.Record],
    ) -> Iterable[wikipedia.Record]:
        """Enrich Wikipedia records with their image URLs and yield the records."""

        for record in records:
            try:
                img_url = self.__get_wikipedia_record_image_url(
                    record.abstract_info.url
                )

            except HTTPError:
                self.__logger.warning(
                    f"Error while getting the image URL of Wikipedia article: {record.abstract_info.title}",
                    exc_info=True,
                )
                continue

            record.abstract_info.imageUrl = img_url
            yield record

    def __clean_wikipedia_title(self, wikipedia_title: Title) -> Title:
        """Remove `WIKIPEDIA_TITLE_PREFIX` from a Wikipedia title."""

        if wikipedia_title.startswith(WIKIPEDIA_TITLE_PREFIX):
            return wikipedia_title[len(WIKIPEDIA_TITLE_PREFIX) :].strip()

        return wikipedia_title

    def __clean_wikipedia_titles(
        self, records: Iterable[wikipedia.Record]
    ) -> Iterable[wikipedia.Record]:
        """Remove unwanted text from the titles of Wikipedia articles."""

        for record in records:
            record.abstract_info.title = self.__clean_wikipedia_title(
                record.abstract_info.title
            )
            yield record

    def __get_featured_articles_urls(self) -> tuple[AnyUrl, ...]:
        """Retrieve URLs of featured Wikipedia articles."""

        featured_articles_urls = [
            cleaned_url
            for cleaned_url in (
                str(url.get("href"))
                for url in BeautifulSoup(
                    self.__session.get(WikipediaUrl.FEATURED_ARTICLES_URL).text,
                    "html.parser",
                ).findAll("a")
            )
            if cleaned_url[: len(WIKI_SUBDIRECTORY)] == WIKI_SUBDIRECTORY
        ]

        featured_articles_urls.sort()

        return tuple(
            AnyUrl(WikipediaUrl.BASE_URL + featured_article_url)
            for featured_article_url in featured_articles_urls
        )

    def __get_featured_records(
        self,
        records: Iterable[wikipedia.Record],
    ) -> Iterable[wikipedia.Record]:
        """Retrieve a list of featured Wikipedia article URLs and yield records that match the URLs."""

        featured_articles_urls = self.__get_featured_articles_urls()

        for record in records:
            if record.abstract_info.url in featured_articles_urls:
                yield record

    def __get_wikipedia_records(
        self, cached_file_path: Path
    ) -> Iterable[wikipedia.Record]:
        """Parse Wikipedia abstracts and return a tuple of Wikipedia records."""

        # Setup parser
        parser = sax.make_parser()  # noqa: S317
        parser.setFeature(sax.handler.feature_namespaces, 0)

        # Instantiate SAX Handler and run parser
        handler = WikipediaAbstractsParser()
        parser.setContentHandler(handler)
        parser.parse(cached_file_path)

        return handler.records

    def __get_wikipedia_record_categories(
        self, wikipedia_article_url: AnyUrl
    ) -> tuple[wikipedia.Category, ...]:
        """Return a tuple of a Wikipedia article's categories."""

        return tuple(
            wikipedia.Category(
                text=category_item.get("href"), link=category_item.text.strip()
            )
            for category_item in BeautifulSoup(  # type: ignore[union-attr]
                self.__session.get(str(wikipedia_article_url)).text, "html.parser"
            )
            .find("a", {"title": "Help:Category"})
            .find_next_sibling()
            .findAll("a")
        )

    def __get_wikipedia_record_external_links(
        self, wikipedia_title: Title
    ) -> tuple[wikipedia.ExternalLink, ...]:
        """Return a tuple of external Wikipedia article links on a Wikipedia page."""

        return tuple(
            wikipedia.ExternalLink(
                title=wikipedia_json["*"].title(),
                link=WikipediaUrl.WIKI_SUBDIRECTORY_URL
                + wikipedia_json["*"].replace(" ", "_"),
            )
            for wikipedia_json in self.__session.get(
                url=WikipediaUrl.MEDIA_WIKI_API,
                params={
                    "action": "parse",
                    "page": self.__clean_wikipedia_title(wikipedia_title),
                    "format": "json",
                },
            ).json()["parse"]["links"]
            if wikipedia_json["ns"] == 0
        )

    def __get_wikipedia_record_image_url(
        self, wikipedia_article_url: AnyUrl
    ) -> AnyUrl | None:
        """Retrieve the ImageURL of a Wikipedia record."""

        img_url = None
        soup = BeautifulSoup(
            self.__session.get(str(wikipedia_article_url)).text, "html.parser"
        )

        file_description_element = soup.find("a", {"class": "mw-file-description"})

        if file_description_element:
            file_description = file_description_element["href"][len(WIKI_SUBDIRECTORY) :]  # type: ignore[index]

        # Get a better resolution of the Wikipedia image.
        if file_description:
            minimum_image_width = 500
            img_url = self.__select_wikipedia_image_resolution(
                str(file_description), minimum_image_width
            )

        # If no better resolution is found, use existing image url on Wikipedia page.
        if img_url is None:
            image_url = str(
                soup.find(  # type: ignore[union-attr, assignment]
                    "a", {"class": "mw-file-description"}
                )
                .findChild()
                .get("src", None)
            )

            img_url = AnyUrl("https://" + image_url)

        return img_url

    def __select_enhancer_callables(
        self,
    ) -> tuple[Callable[[Iterable[wikipedia.Record]], Iterable[wikipedia.Record]], ...]:
        """
        Return a tuple of callables that will be used to transform records.

        Callables are selected based on values in `wikipedia_config`.
        """

        callables: list[
            Callable[[Iterable[wikipedia.Record]], Iterable[wikipedia.Record]]
        ] = []

        if self.wikipedia_config.subset_specifications:
            for specification in self.wikipedia_config.subset_specifications:
                if specification == SubsetSpecification.FEATURED:
                    callables.extend([self.__get_featured_records])

        if self.wikipedia_config.enrichments:
            for enrichment in self.wikipedia_config.enrichments:
                if enrichment == EnrichmentType.IMAGE_URL:
                    callables.append(self.__add_image_url_to_records)

                if enrichment == EnrichmentType.CATEGORY:
                    callables.append(self.__add_categories_to_records)

                if enrichment == EnrichmentType.EXTERNAL_LINK:
                    callables.append(self.__add_external_links_to_records)

        if self.wikipedia_config.clean_wikipedia_title:
            callables.append(self.__clean_wikipedia_titles)

        return tuple(callables)

    def __select_wikipedia_image_resolution(
        self, file_description: NonBlankString, minimum_image_width: int
    ) -> AnyUrl | None:
        """
        Retrieve a high-quality image from Wikimedia Commons API.

        `minimum_image_width` is used as a guide to select the best image from the API.
        """

        base_url = "https://api.wikimedia.org/core/v1/commons/file/"
        url = base_url + file_description

        response = dict(
            json.loads(self.__session.get(url, headers={"User-agent": "Imlapps"}).text)
        )

        display_title = response.get("title", "")
        selected_image_url = None

        try:
            # Select an image in increasing order of preference.
            if ("preferred" in response) and (
                response["preferred"].get("width", 0) >= minimum_image_width
            ):
                selected_image_url = AnyUrl(response["preferred"].get("url", None))
            elif "original" in response:
                selected_image_url = AnyUrl(response["original"].get("url", None))
            elif "thumbnail" in response:
                selected_image_url = AnyUrl(response["thumbnail"].get("url", None))

            # If no image is selected, settle for an image with a width less than the minimum_image_width.
            if (
                selected_image_url is None
                and ("preferred" in response)
                and response["preferred"].get("url") != ""
            ):
                selected_image_url = AnyUrl(response["preferred"].get("url"))

        except HTTPError:
            self.__logger.warning(
                f"Error while selecting an image URL for {display_title} from Wikimedia Commons.",
                exc_info=True,
            )
        return selected_image_url

    def get_records(self, context: dict | None) -> Iterable[dict]:  # noqa: ARG002
        """Generate a stream of Wikipedia records."""

        try:
            cached_file_path = FileCache(
                cache_dir_path=self.wikipedia_config.cache_directory_path
            ).get_file(self.wikipedia_config.abstracts_dump_url)
        except HTTPError:
            self.__logger.warning(
                f"Error while downloading Wikipedia dump from {self.wikipedia_config.abstracts_dump_url}",
                exc_info=True,
            )

        # Apply callables to records and yield.
        for record in reduce(
            lambda x, y: y(x),
            self.__select_enhancer_callables(),
            self.__get_wikipedia_records(cached_file_path),
        ):
            yield record.model_dump()
