'''
Created on Mar 25, 2015

@author: Pace
'''
from bowser.systems.event import EventTarget, Event
from bowser.xmlparse import Element, XmlType, XmlAttributeSetter, XmlElements
from bowser.systems.focus import FocusRequestEvent, FocusEvent
from bowser.systems.key_and_frame import create_navigation_controller,\
    NavigationTheme

class LocationChangedEvent(Event):
    
    name = 'location'
    
    def __init__(self, old_value, new_value):
        Event.__init__(self, LocationChangedEvent.name, synchronous=True, bubbles=True)
        self.old_value = old_value
        self.new_value = new_value

class Window(EventTarget):
    
    def __init__(self, event_dispatcher):
        EventTarget.__init__(self)
        self.__location = None
        self.__root_element = None
        self.event_dispatcher = event_dispatcher
        self.parent = None
        
    @property
    def location(self):
        return self.__location
    
    @location.setter
    def location(self, new_value):
        old_value = self.__location
        self.__location = new_value
        self.dispatch_event(LocationChangedEvent(old_value, new_value))
        
    @property
    def root_element(self):
        return self.__root_element
    
    @root_element.setter
    def root_element(self, value):
        if self.__root_element is not None:
            self.__root_element.parent = None
        self.__root_element = value
        self.__root_element.parent = self
        self.__root_element.focus()
    
class RomElement(Element, EventTarget):
    
    def __init__(self, tag_name, parent_element):
        Element.__init__(self, tag_name, parent_element)
        EventTarget.__init__(self)
        self.classes = []
        self.shortcut_keys = None
        self.focusable = True
        self.text = None
        
    @XmlAttributeSetter("class")
    def _set_classes(self, value):
        self.classes = value.split()
        
    @XmlAttributeSetter("shortcut_key")
    def _set_shortcut_keys(self, value):
        self.shortcut_keys = value.split()

    def focus(self):
        self.dispatch_event(FocusRequestEvent())
        
    def __str__(self):
        return "{0}({1})".format(self.name, self.id)

@XmlType("ram")
class RamDocument(RomElement):
    
    def __init__(self, tag_name, parent_element):
        RomElement.__init__(self, tag_name, parent_element)
        self.focusable = False

@XmlType("container")
@XmlElements(["title"])
class Container(RomElement):
    
    def __init__(self, tag_name, parent_element):
        RomElement.__init__(self, tag_name, parent_element)
        self.remember_position = False
        self.__current_index = None
        self.title = None
        self.navigation_theme = None
        self.add_event_listener(FocusEvent.focus_name, self.__on_focus)
        
    def initialize(self):
        self.__add_navigation_controller()
        
    def navigate_forwards(self):
        if self.__current_index is None:
            if self.__has_real_children():
                self.__current_index = 0
            else:
                return
        else:
            if self.__current_index < (self.__num_real_children() - 1):
                self.__current_index += 1
            else:
                return
        self.__get_real_child(self.__current_index).focus()
    
    def navigate_backwards(self):
        if self.__current_index is None:
            return
        if self.__current_index == 0:
            return
        self.__current_index -= 1
        self.__get_real_child(self.__current_index).focus()
        
    def __get_real_child(self, index):
        real_index = 0
        for child in self.children:
            if child == self.title[0]:
                continue
            if real_index == index:
                return child
            else:
                real_index += 1
        raise Exception("Index out of bounds: {0}".format(index))
        
    def __add_navigation_controller(self):
        if self.navigation_theme is None:
            create_navigation_controller(NavigationTheme.HORIZONTAL, self)
        else:
            create_navigation_controller(self.navigation_theme, self)
        
    def __num_real_children(self):
        if self.title is None:
            return len(self.children)
        else:
            return len(self.children) - 1
        
    def __has_real_children(self):
        return self.__num_real_children() > 0
        
    def __get_component_to_focus_on_reset(self):
        if self.title is not None:
            return self.title[0]
        if self.__current_index is None:
            if self.__has_real_children():
                self.__current_index = 0
            else:
                return None
        return self.__get_real_child(self.__current_index)
        
    def __on_focus(self, focus_event):
        if focus_event.target == self:
            if not self.remember_position:
                self.__current_index = None
            component = self.__get_component_to_focus_on_reset()
            if component is not None:
                component.focus()
                focus_event.stop_propagation()
        
@XmlType("p")
class Paragraph(RomElement):
    
    def __init__(self, tag_name, parent_element):
        RomElement.__init__(self, tag_name, parent_element)
