'''
Created on Mar 24, 2015

@author: pace
'''
from lxml import etree

class XmlParser(object):
    
    def __init__(self, processors, default_element_class):
        lookup = etree.ElementDefaultClassLookup(element=default_element_class)
        self.parser = etree.XMLParser()
        self.parser.set_element_class_lookup(lookup)
        self.processors = processors

    def __post_process_element(self, xml_element):
        for processor in self.processors:
            processor.process(xml_element)
    
    def __post_process_tree(self, xml_tree):
        xml_tree.dfs_do(self.__post_process_element)
        
    def fromstring(self, xml_text):
        root_element = etree.fromstring(xml_text, parser=self.parser)
        self.__post_process_tree(root_element)
        return root_element
    
    def parse(self, file_like_object):
        root_element = etree.parse(file_like_object, parser=self.parser).getroot()
        self.__post_process_tree(root_element)
        return root_element