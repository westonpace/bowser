'''
Created on Mar 29, 2015

@author: Pace
'''
import logging
import string

import pygame

from bowser.systems.event import Event


class KeyCombo(object):
    
    def __init__(self, combo_string):
        combos = combo_string.strip().split()
        if len(combos) > 1:
            raise Exception("Don't have logic in place yet for parsing multi-combos")
        parts = combos[0].split('+')
        if len(parts) > 1:
            self.__modifiers = self.__parse_modifiers(parts[:-1])
        else:
            self.__modifiers = 0
        self.__key = self.__parse_key(parts[-1])
    
    def __parse_modifiers(self, modifiers):
        result = 0
        for modifier in modifiers:
            try:
                result |= getattr(pygame, "KMOD_{0}".format(modifier.upper()))
            except AttributeError:
                raise Exception("The modifier {0} is not a valid modifier".format(modifier))
        return result 
    
    def __parse_key(self, key):
        try:
            key_string = key.lower() if key in string.ascii_letters else key.upper()
            return getattr(pygame, 'K_{0}'.format(key_string))
        except AttributeError:
            raise Exception("The key {0} is not a valid key".format(key))
    
    def matches(self, event):
        if event.modifiers & self.__modifiers != self.__modifiers:
            return False
        return event.key_code == self.__key

class LinearNavigationController(object):
    
    def __init__(self, navigable_object, forward_key, backward_key):
        self.__target = navigable_object
        self.__target.add_event_listener(KeyEvent.name, self.__on_key)
        self.forward_key = forward_key
        self.backward_key = backward_key
        
    def __on_key(self, event):
        if self.forward_key.matches(event):
            self.__target.navigate_forwards()
        elif self.backward_key.matches(event):
            self.__target.navigate_backwards()

class NavigationTheme(object):
    
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    REVERSE_HORIZONTAL = "reverse_horizontal"
    REVERSE_VERTICAL = "reverse_vertical"
    
def create_navigation_controller(theme, target):
    theme_str = theme.lower()
    if theme_str == NavigationTheme.HORIZONTAL:
        return LinearNavigationController(target, KeyCombo("RIGHT"), KeyCombo("LEFT"))
    elif theme_str == NavigationTheme.VERTICAL:
        return LinearNavigationController(target, KeyCombo("DOWN"), KeyCombo("UP"))
    if theme_str == NavigationTheme.REVERSE_HORIZONTAL:
        return LinearNavigationController(target, KeyCombo("LEFT"), KeyCombo("RIGHT"))
    elif theme_str == NavigationTheme.REVERSE_VERTICAL:
        return LinearNavigationController(target, KeyCombo("UP"), KeyCombo("DOWN"))
    else:
        raise Exception("Unrecongzied navigation_theme value: {0}".format(theme))

class KeyEvent(Event):
    
    name = 'key'
    
    def __init__(self, key_code, modifiers):
        Event.__init__(self, KeyEvent.name, synchronous=True, bubbles=True)
        self.key_code = key_code
        self.modifiers = modifiers

class PygameUserEvent(Event):
    
    name = 'pygame_user'
    
    def __init__(self, event_code):
        Event.__init__(self, PygameUserEvent.name, synchronous=True, bubbles=True)
        self.event_code = event_code

class KeyAndFrameEngine(object):

    def __init__(self, focus_system, global_event_bus):
        self.focus_system = focus_system
        self.global_event_bus = global_event_bus
        self.logger = logging.getLogger(__name__)

    def __del__(self):
        pygame.quit()

    def initialize(self):
        pygame.display.init()
        pygame.display.set_mode((100, 100))

    def iterate(self):
        pygame.display.flip()
        events = pygame.event.get()
        self.__process_events(events)
        
    def __process_events(self, events):
        for event in events:
            if event.type == pygame.KEYUP:
                self.logger.debug("Key press: code=%s mod=%s", event.key, event.mod)
                if self.focus_system is not None:
                    self.focus_system.currently_focused.dispatch_event(KeyEvent(event.key, event.mod))
            elif event.type >= pygame.USEREVENT:
                self.logger.debug("User event: code=%s", event.type)
                self.global_event_bus.dispatch_event(PygameUserEvent(event.type))
            elif event.type == pygame.QUIT:
                import sys
                sys.exit(0)
