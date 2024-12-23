from typing import Any
from xml import sax

from pydantic import AnyUrl

from tap_wikipedia.constants import WikipediaUrl
from tap_wikipedia.models import wikipedia


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts."""

    def __init__(self):
        self.__records: list[wikipedia.Record] = []
        self.__abstract_info: wikipedia.AbstractInfo | None
        self.__char_buffer: list[str] = []
        self.__current_data: str
        self.__sublinks: list[wikipedia.Sublink]

    # reset character buffer and return all its contents as a string
    def flush_char_buffer(self) -> str:
        data = "".join(self.__char_buffer)
        self.__char_buffer = []
        return data.strip()

    # store individual records and reset abstracts dictionary
    def store_record(self) -> None:
        if self.__abstract_info and self.__sublinks:
            self.__records.append(
                wikipedia.Record(
                    abstract_info=self.__abstract_info, sublinks=tuple(self.__sublinks)
                )
            )
            self.__abstract_info = None
            self.__sublinks = []

    # Call when an element starts
    def startElement(self, tag: str, attributes: Any) -> None:  # noqa: ARG002, ANN401
        self.__current_data = tag
        if tag == "doc":
            self.__abstract_info = wikipedia.AbstractInfo(
                title="",
                url=AnyUrl(WikipediaUrl.BASE_URL),
                abstract="",
            )
            self.__sublinks = []

    # Call when an elements ends
    def endElement(self, tag: str) -> None:
        if self.__abstract_info:
            if tag == "title":
                self.__abstract_info.title = self.flush_char_buffer()
            elif tag == "url":
                self.__abstract_info.url = AnyUrl(self.flush_char_buffer())
            elif tag == "abstract":
                self.__abstract_info.abstract = self.flush_char_buffer()
            elif tag == "anchor":
                sublink = wikipedia.Sublink()
                sublink.anchor = self.flush_char_buffer()
                self.__sublinks.append(sublink)
            elif tag == "link":
                self.__sublinks[-1].link = self.flush_char_buffer()
            elif tag == "doc":
                self.store_record()

    # store each chunk of character data within character buffer
    def characters(self, content: str) -> None:
        if self.__current_data in ("title", "url", "abstract", "anchor", "link"):
            self.__char_buffer.append(content)

    # return a tuple of Wikipedia records
    @property
    def records(self) -> tuple[wikipedia.Record, ...]:
        return tuple(self.__records)
