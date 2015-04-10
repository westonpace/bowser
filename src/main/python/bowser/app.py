'''
Created on Mar 29, 2015

@author: Pace
'''
import os
import time
import logging

from bowser.timer import Timer
from bowser.rom import Window, Container, RamDocument, Paragraph, RomElement
from bowser.systems.resource import ResourceLoader
from bowser.xmlparse import XmlParser
from bowser.systems.focus import FocusSystem
from bowser.systems.key_and_frame import KeyAndFrameEngine
from bowser.systems.audio import AudioSystem, SoundLibrary
from bowser.systems.renderer import RenderingSystem
from bowser.systems.event import EventDispatcher
from bowser.systems.http import HttpService

class BowserLoopTask(object):
    
    class BowserEngine(object):
        
        def __init__(self, engine, engine_init_func):
            self.engine = engine
            self.engine_init_func = engine_init_func
    
    def __init__(self):
        self.engines = []
        
    def add_init_task(self, init_task):
        self.add_engine(None, init_task)
        
    def add_engine(self, engine, engine_init_func=None):
        self.engines.append(BowserLoopTask.BowserEngine(engine, engine_init_func))
        
    def initialize(self):
        for engine in self.engines:
            if engine.engine_init_func is not None:
                engine.engine_init_func()
        self.engines = [engine_record for engine_record in self.engines if engine_record.engine is not None]
        
    def iterate(self):
        for engine in self.engines:
            engine.engine.iterate()

class Bowser(object):
    
    def __initialize_logging(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
                            level=logging.DEBUG)

    def __create_sound_library(self):
        effects_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), "sounds/effects"))
        library = SoundLibrary(effects_dir)
        return library
    
    def __init__(self):
        self.__initialize_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing bowser")
        self.loop_task = BowserLoopTask()
        self.app_thread = Timer(self.loop_task.iterate, 1/30, self.loop_task.initialize)
        self.event_dispatcher = EventDispatcher()
        self.window = Window(self.event_dispatcher)
        self.parser = XmlParser([Container, RamDocument, Paragraph], RomElement, self.event_dispatcher)
        self.http_service = HttpService()
        self.resource_loader = ResourceLoader(self.window, self.parser, self.http_service)
        self.focus_system = FocusSystem(self.window)
        self.key_and_frame = KeyAndFrameEngine(self.focus_system, self.window)
        self.audio_system = AudioSystem(self.window)
        self.sound_library = self.__create_sound_library()
        self.renderer = RenderingSystem(self.window, self.audio_system)
        self.loop_task.add_engine(self.key_and_frame, self.key_and_frame.initialize)
        self.loop_task.add_engine(self.audio_system, self.audio_system.initialize)
        self.loop_task.add_init_task(self.sound_library.load)
    
    def start(self, initial_location):
        self.logger.info("Starting bowser")
        self.app_thread.start()
        self.app_thread.wait_for_initialized()
        self.window.location = initial_location
    
    def join(self):
        self.app_thread.join()
    
    def stop(self):
        self.app_thread.stop()
        