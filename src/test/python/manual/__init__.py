from bowser.xmlparse import XmlParser
from bowser.rom import RomElement
from bowser.rom import RamDocument
from bowser.rom import Paragraph
from bowser.rom import Container

parser = XmlParser([RamDocument, Paragraph, Container], RomElement)
rom = parser.parse(open('/Users/Pace/pispace/bowser/src/test/python/manual/albums.ram'))
rom.dfs_do(lambda x: print(x))