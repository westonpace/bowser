'''
Created on Mar 29, 2015

@author: Pace
'''
import logging
import urllib

from io import BytesIO
from bowser.rom import LocationChangedEvent
from bowser.systems.http import HttpRequest
from xml.sax import xmlreader

class ResourceLoader(object):
    
    def __init__(self, window, parser, http_service):
        self.__window = window
        self.__parser = parser
        self.__http_service = http_service
        self.__window.add_event_listener(LocationChangedEvent.name, self.__on_location_change)
        self.logger = logging.getLogger(__name__)
        
    def __on_location_change(self, _):
        self.__load_new_location(self.__window.location)
        
    def __load_new_location(self, new_location):
        self.__load_resource(new_location)
        
    def __initialize_element(self, element):
        if hasattr(element, 'initialize'):
            element.initialize()
        
    def __initialize_resource(self, resource):
        resource.dfs_do(self.__initialize_element)

    def __on_resource_load(self, resource):
        self.__window.root_element = resource
        
    def __load_file_resource(self, url):
        #TODO: Asynchronous?
        resource_file = open(url)
        resource = self.__parser.parse(resource_file)
        self.__initialize_resource(resource)
        self.__on_resource_load(resource)
    
    def __on_http_load(self, headers, content):
        resource = self.__parser.parse(BytesIO(content))
        self.__initialize_resource(resource)
        self.__on_resource_load(resource)
    
    def __on_http_failure(self, response):
        self.logger.error("Failed to load URL.  Response Code: %s", response.status)
    
    def __load_http_resource(self, url):
        request = HttpRequest(url)
        self.__http_service.get(request).success(self.__on_http_load).error(self.__on_http_failure)
    
    def __load_resource(self, url):
        parsed_url = urllib.parse.urlparse(url)
        self.logger.info("Loading resource (scheme=%s): %s", parsed_url.scheme, url)
        if parsed_url.scheme in ["http", "https"]:
            self.__load_http_resource(url)
        elif parsed_url.scheme in [None, "file", ""]:
            self.__load_file_resource(parsed_url.path)
        elif len(parsed_url.scheme) == 1:
            raise Exception("Unrecognized URL scheme: {0}  Did you pass in a windows path?  Use file:///C:/...".format(parsed_url.scheme))
        else:
            raise Exception("Unrecognized URL scheme: {0}".format(parsed_url.scheme))
