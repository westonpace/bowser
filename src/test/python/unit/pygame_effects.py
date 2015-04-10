'''
A module for testing pygame effects channels
'''
import os
import time
import unittest

from bowser.systems.audio import PygameEffectsChannel, SoundLibrary
from bowser.systems.event import EventTarget, EventDispatcher
from bowser.systems.key_and_frame import KeyAndFrameEngine
from bowser.timer import Timer

class PygameEffectsChannelTest(unittest.TestCase):
    
    CHIME_NAME = 'chime'
    CHIME_LENGTH = 0.63
    
    event_dispatcher = None
    event_bus = None
    pygame = None
    timer = None
    
    @classmethod
    def setUpClass(cls):
        super(PygameEffectsChannelTest, cls).setUpClass()
        cls.event_dispatcher = EventDispatcher()
        cls.event_bus = EventTarget(cls.event_dispatcher)
        cls.pygame = KeyAndFrameEngine(focus_system=None, global_event_bus=cls.event_bus)
        cls.timer = Timer(task=cls.pygame.iterate, duration_in_seconds=1/30, init_func=cls.pygame.initialize)
        cls.timer.start()
        cls.timer.wait_for_initialized()
        cls.sounds = SoundLibrary(folder=os.path.join(os.path.dirname(__file__), "../../../main/python/bowser/sounds/effects"))
        cls.sounds.load()
        cls.channel = PygameEffectsChannel(channel_id=0, event_bus=PygameEffectsChannelTest.event_bus)
        cls.channel.initialize()
        
    @classmethod
    def tearDownClass(cls):
        super(PygameEffectsChannelTest, cls).tearDownClass()
        cls.timer.stop()
    
    def test_multiple_sounds(self):
        #Play 3 sounds and ensure they get queued properly.  For testing we are just going to take the length of the
        #chime effect and ensure at least 3xlength seconds passed.
        chime = PygameEffectsChannelTest.sounds.get_effect(PygameEffectsChannelTest.CHIME_NAME)
        start = time.time()
        PygameEffectsChannelTest.channel.queue(chime)
        PygameEffectsChannelTest.channel.queue(chime)
        future = PygameEffectsChannelTest.channel.queue(chime)
        future.join()
        elapsed = time.time() - start
        self.assertGreater(elapsed, PygameEffectsChannelTest.CHIME_LENGTH * 3, "It should have taken longer for all 3 sounds to play")
        
    def test_interrupt(self):
        chime = PygameEffectsChannelTest.sounds.get_effect(PygameEffectsChannelTest.CHIME_NAME)
        start = time.time()
        first_future = PygameEffectsChannelTest.channel.queue(chime)
        for _ in range(9):
            last_future = PygameEffectsChannelTest.channel.queue(chime)
        time.sleep(PygameEffectsChannelTest.CHIME_LENGTH * 2)
        PygameEffectsChannelTest.channel.interrupt()
        last_future.join()
        self.assertTrue(first_future.finished)
        self.assertFalse(first_future.cancelled)
        self.assertTrue(last_future.finished)
        self.assertTrue(last_future.cancelled)
        elapsed = time.time() - start
        self.assertLess(elapsed, PygameEffectsChannelTest.CHIME_LENGTH * 10, "It seems like all 10 chimes ran before cancelling")
        