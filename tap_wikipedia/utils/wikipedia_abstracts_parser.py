from pydantic import BaseModel

import xml.sax as sax
from typing import List, Dict, Tuple


class _EntityXML(BaseModel):
    """A Pydantic Model to contain Wikipedia Abstracts"""

    class AbstractInfo(BaseModel):
        title: str = ""
        abstract: str = ""
        url: str = ""

    class Sublink(BaseModel):
        anchor: str = ""
        link: str = ""

    abstract_info: AbstractInfo = AbstractInfo()
    sublinks: List[Sublink] = []


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts"""

    def __init__(self):
        self.currentData = ""
        self.charBuffer: List[str] = []
        self._records: List[Dict] = []
        self.abstractData = _EntityXML()

    # reset character buffer and return all its contents as a string
    def __flush_char_buffer(self):
        data = "".join(self.charBuffer)
        self.charBuffer = []
        return data.strip()

    # store individual records and reset abstracts dictionary
    def __store_record(self):
        record = self.abstractData.model_dump()

        self._records.append(record)
        self.abstractData = _EntityXML()

    # Call when an element starts
    def startElement(self, tag, attributes):
        self.currentData = tag
        if tag == "doc":
            self.abstractData.abstract_info = _EntityXML.AbstractInfo()
            self.abstractData.sublinks = []

    # Call when an elements ends
    def endElement(self, tag):
        if tag == "title":
            self.abstractData.abstract_info.title = self.__flush_char_buffer()
        elif tag == "url":
            self.abstractData.abstract_info.url = self.__flush_char_buffer()
        elif tag == "abstract":
            self.abstractData.abstract_info.abstract = (
                self.__flush_char_buffer()
            )  # noqa: E501
        elif tag == "anchor":
            sublink = _EntityXML.Sublink()
            sublink.anchor = self.__flush_char_buffer()
            self.abstractData.sublinks.append(sublink)
        elif tag == "link":
            self.abstractData.sublinks[-1].link = self.__flush_char_buffer()
        elif tag == "doc":
            self.__store_record()

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

    # return a Tuple of records
    @property
    def records(self) -> Tuple[Dict, ...]:
        return tuple(self._records)
