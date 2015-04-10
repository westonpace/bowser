'''
Created on Mar 29, 2015

@author: Pace
'''
from threading import Thread, Condition
import time
import logging
class Timer(object):
    
    def __init__(self, task, duration_in_seconds, init_func=None):
        self.__task = task
        self.__init_func = init_func
        self.__stopping = False
        self.__thread = None
        self.__initialized_condition = Condition()
        self.__initialized = False
        self.__duration = duration_in_seconds
        self.logger = logging.getLogger(__name__)
        
    def start(self):
        self.__thread = Thread(target=self.run)
        self.__thread.start()
        
    def stop(self):
        self.__stopping = True
        self.__thread.join()
        
    def wait_for_initialized(self):
        with self.__initialized_condition:
            while not self.__initialized:
                self.__initialized_condition.wait()
            
    def join(self):
        self.__thread.join()
        
    def run(self):
        try:
            if self.__init_func is not None:
                self.__init_func()
            with self.__initialized_condition:
                self.__initialized = True
                self.__initialized_condition.notify_all()
            while not self.__stopping:
                started = time.time()
                self.__task()
                remaining = (self.__duration - (time.time() - started))
                if remaining > 0:
                    time.sleep(remaining)
        except:
            self.logger.exception("Exception occurred in timer thread")
                