'''
Created on Mar 25, 2015

@author: Pace
'''
from concurrent.futures import ThreadPoolExecutor
import logging
import time


class Event(object):
    '''
    Represents an event in the system.  For more details on event propagation 
    see :class:`EventDispatcher`.

    type
        The name of the event (e.g. keypress)
    target
        The original source of the event, this does not change as the event propagates
    current_target
        The current target of the event, this changes as the event propagates
    timestamp
        The time at which the event was dispatched
    synchronous
        True if this event will be dispatched synchronously or False if dispatched asynchronously
    bubbles
        True if this event will bubble up, or False if it will only be emitted at the target
    event_phase
        The phase the event is currently in.
    '''
    #Have to have lots of instance variables to comply with DOM
    # pylint: disable=too-many-instance-attributes

    #: Events in this phase have not yet been dispatched or have been finished disptaching
    NONE = 0
    #: Events in this phase are capturing (moving down from window to target)
    CAPTURING_PHASE = 1
    #: Events in this phase are being emitted at the target
    AT_TARGET = 2
    #: Events in this phase are bubbling up (moving up from target to window)
    BUBBLING_PHASE = 3

    def __init__(self, event_type, synchronous=True, bubbles=True):
        self.name = event_type
        self.target = None
        self.current_target = None
        self.timestamp = None
        self.synchronous = synchronous
        self.bubbles = bubbles
        self.event_phase = Event.NONE
        self.__immediate_propagate = True
        self.__propagate = True

    def should_propagate(self):
        '''
        Mainly for internal use, this returns True if the event should still propagate
        '''
        return self.__propagate

    def should_propagate_immediately(self):
        '''
        Mainly for internal use, this returns True if the event should still propagate immediately
        '''
        return self.__immediate_propagate

    def stop_propagation(self):
        '''
        Stops propagation of the event, the event will not be dispatched on any other event targets
        '''
        self.__propagate = False

    def stop_immediate_propagation(self):
        '''
        Stops immediate propagation of the event.

        The difference between this and :meth:stop_propagation is that this will prevent
        any listeners being called where :meth:stop_propagation will finish dispatching
        at the current target.
        '''
        self.__propagate = False
        self.__immediate_propagate = False

    def __str__(self):
        return "<{0}({1}) at 0x{2:X}>".format(self.__class__.__name__, self.name, id(self))

class EventDispatcher(object):
    '''
    Dispatches events.

    When an event is dispatched on a target the event goes through a number of phases.  For a
    complete description of these phases please see http://www.w3.org/TR/DOM-Level-3-Events/.

    The first phase is the capturing phase.  In this phase the event works its way down from
    the top-level-element (the window) to the target.  Listeners must have been registered 
    with use_capture=True in order to catch events in this phase.  Listeners can catch events
    in this phase and then prevent them from propagating further downwards.

    Once the event reaches the target the event is dispatched on the target, this is called
    the target phase and listeners registered on the target with use_capture=False will be
    called.

    If the event is set to bubble (bubbles=True) then a bubbling phase will occur.  The event
    will travel upwards, from the target to the top level window and listeners that have
    been registered with use_capture=False will be triggered.
    '''

    def __init__(self):
        self.__async_executor = ThreadPoolExecutor(max_workers=10)
        self.logger = logging.getLogger(__name__)
        self._listeners_map = {}
        self._capture_listeners_map = {}

    def __do_fire_event(self, event, target):
        '''
        Actually fires the event
        '''
        try:
            _EventExecution(event, target).fire()
        #pylint: disable=bare-except
        except:
            self.logger.exception("Error occurred dispatching event: %s", event)

    def fire_event(self, event, target):
        '''
        Fires an event either synchronously or asynchronously depending on the event
        '''
        if event.synchronous:
            self.__do_fire_event(event, target)
        else:
            self.__async_executor.submit(self.__do_fire_event, event, target)

GLOBAL_DISPATCHER = EventDispatcher()
  
class _EventExecution(object):
    '''
    Command to execute an individual event
    '''

    def __init__(self, event, target):
        self.__event = event
        self.__target = target
        self.__propagation_path = []
        self.logger = logging.getLogger(__name__)

    def __calculate_propagation_path(self):
        path = []
        target = self.__target.getparent()
        while target is not None:
            path.append(target)
            target = target.getparent()
        return list(reversed(path))

    def __fire_on_listeners(self, listeners):
        for listener in listeners:
            listener(self.__event)
            if not self.__event.should_propagate_immediately():
                return

    def __relocate_event(self, event_target):
        self.__event.current_target = event_target

    def __get_capture_listeners(self, target):
        if self.__event.name in target.capture_listeners:
            return target.capture_listeners[self.__event.name]
        else:
            return []
        
    def __get_listeners(self, target):
        if self.__event.name in target.listeners:
            return target.listeners[self.__event.name]
        else:
            return []

    def __fire_target_phase(self):
        self.__relocate_event(self.__target)
        listeners = self.__get_capture_listeners(self.__target)
        self.__fire_on_listeners(listeners)
        if not self.__event.should_propagate():
            return
        self.__event.event_phase = Event.AT_TARGET
        listeners = self.__get_listeners(self.__target)
        self.__fire_on_listeners(listeners)

    def __fire_capture_phase(self):
        self.__event.event_phase = Event.CAPTURING_PHASE
        for event_target in self.__propagation_path:
            self.__relocate_event(event_target)
            listeners = self.__get_capture_listeners(event_target)
            self.__fire_on_listeners(listeners)
            if not self.__event.should_propagate():
                return

    def __fire_bubbles_phase(self):
        self.__event.event_phase = Event.BUBBLING_PHASE
        if not self.__event.bubbles:
            return
        for event_target in reversed(self.__propagation_path):
            self.__relocate_event(event_target)
            listeners = self.__get_listeners(event_target)
            self.__fire_on_listeners(listeners)
            if not self.__event.should_propagate():
                return

    def fire(self):
        try:
            self.logger.debug("Firing event: %s at target %s", self.__event, self.__target)
            self.__event.timestamp = time.time()
            self.__propagation_path = self.__calculate_propagation_path()
            self.__fire_capture_phase()
            if not self.__event.should_propagate():
                return
            self.__fire_target_phase()
            if not self.__event.should_propagate():
                return
            self.__fire_bubbles_phase()
        finally:
            self.__event.event_phase = Event.NONE
            self.__event.current_target = None
            
class EventTarget(object):
    '''
    A base class for entities which wish to act as event targets.
    
    event_dispatcher
        A reference to the event dispatcher that this target will dispatch events on
    '''

    @property
    def listeners(self):
        '''
        A read only list of listeners for the non-capture phases
        '''
        if self.get_id() not in GLOBAL_DISPATCHER._listeners_map:
            GLOBAL_DISPATCHER._listeners_map[self.get_id()] = {}
        return GLOBAL_DISPATCHER._listeners_map[self.get_id()]

    @property
    def capture_listeners(self):
        '''
        A read only list of listeners for the capture phase
        '''
        if self.get_id() not in GLOBAL_DISPATCHER._capture_listeners_map:
            GLOBAL_DISPATCHER._capture_listeners_map[self.get_id()] = {}
        return GLOBAL_DISPATCHER._capture_listeners_map[self.get_id()]

    def __get_listeners_map(self, use_capture):
        if use_capture:
            return self.capture_listeners
        else:
            return self.listeners

    def __get_listeners_for_type(self, event_type, use_capture, initialize):
        listeners_map = self.__get_listeners_map(use_capture)
        if event_type not in listeners_map:
            if initialize:
                listeners_map[event_type] = []
            else:
                return None
        return listeners_map[event_type]

    def __prune_type_if_possible(self, event_type, use_capture):
        listener_map = self.__get_listeners_map(use_capture)
        if not listener_map[event_type]:
            del listener_map[event_type]

    def add_event_listener(self, event_type, listener, use_capture=False):
        '''
        Adds a listener for a given event_type
        
        event_type
            The event_type to listen for, only events of this type will trigger the listener
        listener
            A callable which takes one parameter (the event)
        use_capture
            If True then this will register the listener for the capture phase and not 
            the other phases.  If False, then this will register the listener for the other 
            phases and not the capture phase.  To catch an event in both phases this method 
            must be called twice
        '''
        self.__get_listeners_for_type(event_type, use_capture, initialize=True).append(listener)

    def remove_event_listener(self, event_type, listener, use_capture=False):
        '''
        Removes a listener previously registered with :meth:`add_event_listener`
        '''
        self.__get_listeners_for_type(event_type, use_capture, initialize=False).remove(listener)
        self.__prune_type_if_possible(event_type, use_capture)

    def dispatch_event(self, event):
        '''
        Dispatches an event at this target
        '''
        event.target = self
        GLOBAL_DISPATCHER.fire_event(event, self)
        