from dataclasses import dataclass
from pydantic import BaseModel
from tap_wikipedia.models import wikipedia
import xml.sax as sax


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts"""

    @dataclass
    class _EntityXML(BaseModel):
        """A Pydantic Model to contain Wikipedia Abstracts"""

        @dataclass
        class AbstractInfo(BaseModel):
            title: str = ""
            abstract: str = ""
            url: str = ""

        @dataclass
        class Sublink(BaseModel):
            anchor: str = ""
            link: str = ""

        abstract_info: wikipedia.AbstractInfo = wikipedia.AbstractInfo()
        sublinks: list[wikipedia.Sublink] = []

    def __init__(self):
        self.currentData = ""
        self.charBuffer: list[str] = []
        self._records: list[WikipediaAbstractsParser._EntityXML] = []
        self.abstractData = WikipediaAbstractsParser._EntityXML()

    # reset character buffer and return all its contents as a string
    def flushCharBuffer(self):
        data = "".join(self.charBuffer)
        self.charBuffer = []
        return data.strip()

    # store individual records and reset abstracts dictionary
    def storeRecord(self):
        self._records.append(self.abstractData)
        self.abstractData = WikipediaAbstractsParser._EntityXML()

    # Call when an element starts
    def startElement(self, tag, attributes):
        self.currentData = tag
        if tag == "doc":
            self.abstractData.abstract_info = (
                WikipediaAbstractsParser._EntityXML().AbstractInfo()
            )
            self.abstractData.sublinks = []

    # Call when an elements ends
    def endElement(self, tag):
        if tag == "title":
            self.abstractData.abstract_info.title = self.flushCharBuffer()
        elif tag == "url":
            self.abstractData.abstract_info.url = self.flushCharBuffer()
        elif tag == "abstract":
            self.abstractData.abstract_info.abstract = (
                self.flushCharBuffer()
            )  # noqa: E501
        elif tag == "anchor":
            sublink = WikipediaAbstractsParser._EntityXML().Sublink()
            sublink.anchor = self.flushCharBuffer()
            self.abstractData.sublinks.append(sublink)
        elif tag == "link":
            self.abstractData.sublinks[-1].link = self.flushCharBuffer()
        elif tag == "doc":
            self.storeRecord()

    # store each chunk of character data within character buffer
    def characters(self, content):
        if self.currentData == "title":
            self.charBuffer.append(content)
        elif self.currentData == "url":
            self.charBuffer.append(content)
        elif self.currentData == "abstract":
            self.charBuffer.append(content)
        elif self.currentData == "anchor":
            self.charBuffer.append(content)
        elif self.currentData == "link":
            self.charBuffer.append(content)

    # return a tuple of wikipedia.Record
    @property
    def records(self) -> tuple[wikipedia.Record, ...]:
        return tuple(
            wikipedia.Record(
                abstract_info=record.abstract_info, sublinks=tuple(
                    record.sublinks)
            )
            for record in self._records
        )
