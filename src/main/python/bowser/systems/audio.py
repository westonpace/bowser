'''
Created on Mar 25, 2015

@author: Pace
'''
import pyttsx
import logging
import os
import pygame
from threading import RLock
from bowser.custom_futures import Future
from bowser.systems.key_and_frame import PygameUserEvent

class SoundLibrary(object):
    
    def __init__(self, folder):
        self.__folder = folder
        self.__sounds = {}
        
    def load(self):
        for filename in os.listdir(self.__folder):
            if filename.endswith(".ogg"):
                name = filename.rpartition('.')[0]
                full_path = os.path.join(self.__folder, filename)
                self.__sounds[name] = pygame.mixer.Sound(file=full_path)
            
    def get_effect(self, name):
        return self.__sounds[name]
    
    def get_effects(self):
        return self.__sounds.values()

class PygameEffectsChannel(object):
    '''
    A Channel is a linear sequence of audio.  Audio requests can be TTS requests,
    requests to play sound effects, background music, etc.  The input to the channel's
    queue method depends on the type of channel (str for tts, etc.)
    
    This is a pgyame channel, it is used for sound effects
    '''
    
    class QueuedEffect(object):
        
        def __init__(self, effect, future):
            self.effect = effect
            self.future = future
    
    def __init__(self, channel_id, event_bus):
        self.__channel = None
        self.__channel_id = channel_id
        self.__queue = []
        self.__playing = False
        self.__queued_to_pygame = 0
        self.__lock = RLock()
        self.__event_bus = event_bus
        self.__event_bus.add_event_listener(PygameUserEvent.name, self.__on_pygame_finish)
        
    def __del__(self):
        self.__event_bus.remove_event_listener(PygameUserEvent.name, self.__on_pygame_finish)
    
    def initialize(self):
        self.__channel = pygame.mixer.Channel(self.__channel_id)
        self.__channel.set_endevent(self.__get_event_code())
    
    def __ready_to_queue_to_pygame(self):
        return self.__queued_to_pygame < 2
    
    def __pop_and_finish(self):
        finished = self.__queue.pop(0)
        if finished is not None:
            finished.future.fulfill()
    
    def __get_event_code(self):
        #pylint: disable=no-member
        return pygame.USEREVENT + self.__channel_id
    
    def __on_pygame_finish(self, event):
        if event.event_code == self.__get_event_code():
            with self.__lock:
                self.__pop_and_finish()
                #self.__queue[0] could be None if we have two sounds playing and get interrupted.
                #In this case we will push two None events into the queue to swallow the two pygame callbacks.
                #When swallowing the first callback self.__queue[0] will be None
                self.__queued_to_pygame -= 1
                if len(self.__queue) > 1 and self.__queue[0] is not None:
                    self.__queue_to_pygame(self.__queue[0].effect)
                
    def __queue_to_pygame(self, effect):
        self.__channel.queue(effect)
        self.__queued_to_pygame += 1
                
    def interrupt(self):
        with self.__lock:
            old_queue = self.__queue
            self.__queue = []
            #If pygame is still playing then pygame will send a finish event when
            #we call stop, so we add a None to prevent that finish event from triggering the future
            for _ in range(self.__queued_to_pygame):
                self.__queue.append(None)
            self.__queued_to_pygame = 0
            self.__channel.stop()
        for old_record in old_queue:
            old_record.future.cancel()
    
    def queue(self, effect):
        future = Future()
        with self.__lock:
            self.__queue.append(PygameEffectsChannel.QueuedEffect(effect, future))
            if self.__ready_to_queue_to_pygame():
                self.__queue_to_pygame(effect)
            return future

class PyttsxChannel(object):
    '''
    A Channel is a linear sequence of audio.  Audio requests can be TTS requests,
    requests to play sound effects, background music, etc.  The input to the channel's
    queue method depends on the type of channel (str for tts, etc.)
    
    This is a pyttsx channel, it is used for TTS and speaks strings
    '''
    
    def __init__(self, name):
        self.name = name
        self.engine = None
        self.logger = logging.getLogger("{0}.{1}".format(__name__, name))
        self.__lock = RLock()
        self.__futures = []
    
    def queue(self, text):
        '''
        Queues a string of text to be spoken by the speech synthesis engine
        '''
        self.logger.debug("Queuing %s", text)
        future = Future()
        with self.__lock:
            self.engine.say(text)
            self.__futures.append(future)
            return future
    
    def initialize(self):
        '''
        Initializes the channel.  A channel must be initialized before it can be
        used.  The initialize function MUST be called on the same thread that will
        be calling the iterate function.
        '''
        self.logger.info("Channel initialized")
        self.engine = pyttsx.init(debug=True)
        self.engine.startLoop(useDriverLoop=False)
        self.engine.connect('finished-utterance', self.__on_utterance_finished)
    
    #pylint: disable=unused-argument
    def __on_utterance_finished(self, completed, *args, **kwargs):
        if completed:
            self.__futures.pop().fulfill()
        else:
            self.__futures.pop().cancel()
    
    def interrupt(self):
        '''
        Interrupts the channel, stopping whatever is currently being spoken and clearing
        out the queue.
        '''
        with self.__lock:
            self.logger.debug("Channel interrupted")
            self.engine.stop()
            self.__futures = []
        
    def _iterate(self):
        '''
        This function must be called on a regular basis so that the channel can continue
        processing.  Preferably at least 10-20 times a second.
        '''
        self.engine.iterate()

class AudioSystem(object):
    '''
    The AudioSystem keeps tracks of a number of named channels.
    '''
        
    def __init__(self, event_bus):
        self.tts_channel = PyttsxChannel('main-tts')
        self.effects_channel = PygameEffectsChannel(0, event_bus)
        
    def initialize(self):
        '''
        Initializes the AudioSystem.  This must be called on the same thread that calls
        the iterate function.
        '''
        pygame.mixer.init(frequency=44100)
        self.tts_channel.initialize()
        self.effects_channel.initialize()
        
    def iterate(self):
        '''
        Iterates the AudioSystem, processing internal events and actions.  This must be
        called on a regular basis, at least 10-20 times a second.
        '''
        #pylint: disable=protected-access
        self.tts_channel._iterate()
                    