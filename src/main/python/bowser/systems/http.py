'''
Created on Apr 6, 2015

@author: Pace
'''
from concurrent.futures.thread import ThreadPoolExecutor
from threading import RLock
from httplib2 import Http
import urllib
import logging

class HttpRequest(object):

    def __init__(self, url, parameters=None, data=None, headers=None):
        self.url = url
        self.parameters = parameters or {}
        self.data = data
        self.headers = headers or {}

#TODO: If response is already set when success/error listener is added we should call the listener on a different
#      thread to more accurately mimic expected behavior.
class HttpFuture(object):

    def __init__(self):
        self.__success_listeners = []
        self.__error_listeners = []
        self.__content = None
        self.__headers = None
        self.__status = None
        self.__mutex = RLock()

    def fulfill(self, headers, content):
        with self.__mutex:
            self.__content = content
            self.__headers = headers
            self.__status = int(headers['status'])
            if self.__status < 400:
                for success_listener in self.__success_listeners:
                    success_listener(headers, content)
            else:
                for error_listener in self.__error_listeners:
                    error_listener(headers, content)
                
    def success(self, listener):
        with self.__mutex:
            if self.__content is None:
                self.__success_listeners.append(listener)
                return self
            elif self.__status < 400:
                listener(self.__headers, self.__content)
    
    def error(self, listener):
        with self.__mutex:
            if self.__content is None:
                self.__error_listeners.append(listener)
                return self
            elif self.__status >= 400:
                listener(self.__headers, self.__content)

class HttpService(object):
    
    def __init__(self):
        self.__async_executor = ThreadPoolExecutor(max_workers=10)
        self.logger = logging.getLogger(__name__)
        self.__http = Http()
    
    def get(self, request):
        return self.make_request(request, 'GET')
    
    def post(self, request):
        return self.make_request(request, 'POST')
    
    def put(self, request):
        return self.make_request(request, 'PUT')
    
    def delete(self, request):
        return self.make_request(request, 'DELETE')
    
    def make_request(self, request, method):
        future = HttpFuture()
        self.__async_executor.submit(self.__do_request, request, method, future)
        return future

    def __do_request(self, request, method, future):
        try:
            uri = request.url + urllib.parse.urlencode(request.parameters)
            headers, content = self.__http.request(uri, method, request.data, request.headers)
            future.fulfill(headers, content)
        except Exception as ex:
            self.logger.exception("Http __do_request attempt failed with exception")
