'''
Created on Mar 25, 2015

@author: Pace
'''
from bowser.systems.event import Event
from bowser import Attributes
import logging

FOCUSABLE_ATTR_NAME = "focusable"

class FocusRequestEvent(Event):
    '''
    This event is dispatched when an element would like to request focus.
    
    This event should only be caught if an application is trying to prevent a focus change.  If an
    application would rather respond to a focus change then FocusEvent or FocusChangedEvent would
    be better.  For more details see :class:FocusSystem
    '''
    
    name = 'focus_request'
    
    def __init__(self):
        Event.__init__(self, FocusRequestEvent.name, synchronous=True, bubbles=True)

class FocusEvent(Event):
    '''
    This event is dispatched on a target when that target loses or gains focus.
    
    The event type will signify whether this is a loss of focus (blur) or a gain of
    focus (focus).
    
    This event does not bubble.  If an application wants to catch all focus changes then
    the application should catch :class:FocusChangeEvent
    '''
    
    focus_name = 'focus'
    blur_name = 'blur'
    
    def __init__(self, name):
        Event.__init__(self, name, synchronous=True, bubbles=True)

class FocusSystem(object):
    
    def __init__(self, focus_tree_root):
        self.logger = logging.getLogger(__name__)
        self.currently_focused = None
        focus_tree_root.add_event_listener(FocusRequestEvent.name, self.__on_focus_requeseted)
        
    def __is_focusable(self, element):
        return element.get_bool(Attributes.Focusable, default_value=True)
        
    def __find_first_focusable_child(self, target):
        return target.dfs(lambda node: self.__is_focusable(node))
        
    def __find_first_focusable_parent(self, target):
        return target.find_first_ancestor(lambda node: self.__is_focusable(node))
        
    def __find_first_focusable(self, target):
        if self.__is_focusable(target):
            return target
        result = self.__find_first_focusable_child(target)
        if result is None:
            result = self.__find_first_focusable_parent(target)
        return result
        
    def __do_focus_change(self, new_target):
        self.logger.debug("Changing focus from: %s to: %s", self.currently_focused, new_target)
        if self.currently_focused is not None:
            self.currently_focused.dispatch_event(FocusEvent(FocusEvent.blur_name))
        self.currently_focused = new_target
        new_target.dispatch_event(FocusEvent(FocusEvent.focus_name))
        
    def __on_focus_requeseted(self, focus_request_event):
        focus_target = focus_request_event.target
        actual_focus_target = self.__find_first_focusable(focus_target)
        if actual_focus_target == self.currently_focused:
            #This is possible if the element and none of its children are focusable
            return
        self.__do_focus_change(actual_focus_target)
            