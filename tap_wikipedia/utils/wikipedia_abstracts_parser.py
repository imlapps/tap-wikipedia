import dataclasses
from dataclasses import dataclass

import xml.sax as sax
from typing import Tuple


@dataclass(frozen=True)
class _EntityXML:
    """Dataclass to contain Wikipedia Abstracts"""

    @dataclass(frozen=True)
    class AbstractInfo:
        title: str
        abstract: str
        url: str

    @dataclass(frozen=True)
    class Sublinks:
        anchor: str
        link: str

    abstract_info: AbstractInfo
    sublinks: Tuple[Sublinks]


class WikipediaAbstractsParser(sax.ContentHandler):
    """SAX Handler for Wikipedia Abstracts"""

    def __init__(self):
        self.CurrentData = ""
        self.charBuffer = []
        self.records = []
        self.abstractInfoDictionary = {}

    # reset character buffer and return all its contents as a string
    def __flush_char_buffer(self):
        data = ''.join(self.charBuffer)
        self.charBuffer = []
        return data.strip()

    # store individual records and reset abstracts dictionary
    def __store_record(self):
        abstract_info = _EntityXML.AbstractInfo(
            title=self.abstractInfoDictionary['title'],
            abstract=self.abstractInfoDictionary['abstract'],
            url=self.abstractInfoDictionary['url']
        )
        sublinks: list[_EntityXML.Sublinks] = []

        for i in range(len(self.abstractInfoDictionary['link'])):
            wikipediaAnchor = self.abstractInfoDictionary["anchor"][i]
            wikipediaLink = self.abstractInfoDictionary['link'][i]
            sublinks.append(_EntityXML.Sublinks(
                anchor=wikipediaAnchor, link=wikipediaLink))

        wikipediaInfo = _EntityXML(
            abstract_info=abstract_info,
            sublinks=tuple(sublinks))

        record = {"info": dataclasses.asdict(wikipediaInfo.abstract_info),
                  "sublinks": tuple([dataclasses.asdict(x) for x in wikipediaInfo.sublinks])}

        self.records.append(record)
        self.abstractInfoDictionary = {}

    # Call when an element starts
    def startElement(self, tag, attributes):
        self.CurrentData = tag

    # Call when an elements ends
    def endElement(self, tag):
        if tag == "title":
            self.abstractInfoDictionary["title"] = self.__flush_char_buffer()
        if tag == "url":
            self.abstractInfoDictionary["url"] = self.__flush_char_buffer()
        if tag == "abstract":
            self.abstractInfoDictionary["abstract"] = self.__flush_char_buffer(
            )
        if tag == "anchor":
            if tag not in self.abstractInfoDictionary:
                self.abstractInfoDictionary["anchor"] = []
            self.abstractInfoDictionary["anchor"].append(
                self.__flush_char_buffer())
        if tag == "link":
            if tag not in self.abstractInfoDictionary:
                self.abstractInfoDictionary["link"] = []
            self.abstractInfoDictionary["link"].append(
                self.__flush_char_buffer())
        if tag == "doc":
            self.__store_record()

    # store each chunk of character data within character buffer
    def characters(self, content):
        if self.CurrentData == "title":
            self.charBuffer.append(content)
        if self.CurrentData == "url":
            self.charBuffer.append(content)
        if self.CurrentData == "abstract":
            self.charBuffer.append(content)
        if self.CurrentData == "anchor":
            self.charBuffer.append(content)
        if self.CurrentData == "link":
            self.charBuffer.append(content)

    # return list of records
    def getRecords(self):
        return self.records
