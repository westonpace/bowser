from concurrent.futures.thread import ThreadPoolExecutor
from threading import Condition
import logging

common_pool = ThreadPoolExecutor(max_workers=1)

class Future(object):
    
    class CallbackRecord(object):
        
        def __init__(self, callback, trigger_on_cancel):
            self.callback = callback
            self.trigger_on_cancel = trigger_on_cancel
    
    def __init__(self):
        self.__result = None
        self.finished = False
        self.cancelled = False
        self.__callbacks = []
        self.__lock = Condition()
        self.logger = logging.getLogger(__name__)
    
    def fulfill(self, result=None):
        with self.__lock:
            print("FULFILL")
            self.__result = result
            self.__do_finish()
        
    def __do_finish(self):
        self.finished = True
        self.__fire_callbacks()
        self.__lock.notify_all()
        
    def cancel(self):
        with self.__lock:
            print("CANCEL")
            self.cancelled = True
            self.__do_finish()
        
    def __fire_callbacks(self):
        for callback_record in self.__callbacks:
            self.__fire_callback(callback_record)
            
    def __do_fire(self, callback):
        #pylint: disable=bare-except
        try:
            callback(self.__result)
        except:
            self.logger.exception("Exception occurred running future callback")
            
    def __fire_callback(self, callback_record):
        if callback_record.trigger_on_cancel or not self.cancelled:
            common_pool.submit(self.__do_fire(callback_record.callback))
        
    def join(self):
        with self.__lock:
            while not self.finished:
                self.__lock.wait()
        
    def add_callback(self, callback, trigger_on_cancel=True):
        callback_record = Future.CallbackRecord(callback, trigger_on_cancel)
        with self.__lock:
            if self.finished:
                self.__fire_callback(callback_record)
            else:
                self.__callbacks.append(callback_record)
