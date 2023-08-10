from dataclasses import dataclass
from dataclasses_json import dataclass_json

import xml.sax as sax
from typing import List, Dict, Tuple


@dataclass(init=False)
class _EntityXML:
    """Dataclass to contain Wikipedia Abstracts"""

    @dataclass_json
    @dataclass(init=False)
    class AbstractInfo:
        title: str
        abstract: str
        url: str

    @dataclass_json
    @dataclass(init=False)
    class Sublink:
        anchor: str
        link: str

    abstract_info: AbstractInfo
    sublinks: List[Sublink]


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts"""

    def __init__(self):
        self.CurrentData = ""
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
        wikipediaInfo = self.abstractData
        record = {
            "info": wikipediaInfo.abstract_info.to_dict(),
            "sublinks": tuple(
                _EntityXML.Sublink.schema().dump(wikipediaInfo.sublinks, many=True)
            ),
        }

        self._records.append(record)
        self.abstractData = _EntityXML()

    # Call when an element starts
    def startElement(self, tag, attributes):
        self.CurrentData = tag
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
            self.abstractData.abstract_info.abstract = self.__flush_char_buffer()
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
        if self.CurrentData == "title":
            self.charBuffer.append(content)
        elif self.CurrentData == "url":
            self.charBuffer.append(content)
        elif self.CurrentData == "abstract":
            self.charBuffer.append(content)
        elif self.CurrentData == "anchor":
            self.charBuffer.append(content)
        elif self.CurrentData == "link":
            self.charBuffer.append(content)

    # return a Tuple of records
    @property
    def records(self) -> Tuple[Dict, ...]:
        return tuple(self._records)
