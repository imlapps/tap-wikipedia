from typing import Any

from defusedxml import sax

from tap_wikipedia.models import wikipedia


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts."""

    def __init__(self):
        self._records: list[wikipedia.Record] = []
        self.abstractInfo: wikipedia.AbstractInfo | None
        self.charBuffer: list[str] = []
        self.currentData: str
        self.sublinks: list[wikipedia.Sublink] | None

    # reset character buffer and return all its contents as a string
    def flushCharBuffer(self) -> str:
        data = "".join(self.charBuffer)
        self.charBuffer = []
        return data.strip()

    # store individual records and reset abstracts dictionary
    def storeRecord(self) -> None:
        if self.abstractInfo and self.sublinks:
            self._records.append(
                wikipedia.Record(
                    abstract_info=self.abstractInfo, sublinks=tuple(self.sublinks)
                )
            )

            self.abstractInfo = None
            self.sublinks = None

    # Call when an element starts
    def startElement(self, tag: str, attributes: Any) -> None:  # noqa: ARG002, ANN401
        self.currentData = tag
        if tag == "doc":
            self.abstractInfo = wikipedia.AbstractInfo(title="", url="", abstract="")
            self.sublinks = []

    # Call when an elements ends
    def endElement(self, tag: str) -> None:
        if self.abstractInfo and self.sublinks:
            if tag == "title":
                self.abstractInfo.title = self.flushCharBuffer()
            elif tag == "url":
                self.abstractInfo.url = self.flushCharBuffer()
            elif tag == "abstract":
                self.abstractInfo.abstract = self.flushCharBuffer()
            elif tag == "anchor":
                sublink = wikipedia.Sublink()
                sublink.anchor = self.flushCharBuffer()
                self.sublinks.append(sublink)
            elif tag == "link":
                self.sublinks[-1].link = self.flushCharBuffer()
            elif tag == "doc":
                self.storeRecord()

    # store each chunk of character data within character buffer
    def characters(self, content: str) -> None:
        if self.currentData in ("title", "url", "abstract", "anchor", "link"):
            self.charBuffer.append(content)

    # return a tuple of wikipedia.Record
    @property
    def records(self) -> tuple[wikipedia.Record, ...]:
        return tuple(self._records)
