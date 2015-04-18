'''
Created on Mar 25, 2015

@author: Pace
'''
from bowser.systems.event import EventTarget, Event
from bowser.systems.focus import FocusRequestEvent, FocusEvent
from bowser.systems.key_and_frame import create_navigation_controller, NavigationTheme,\
    KeyEvent
from lxml.etree import ElementBase
from bowser import Attributes, Tags

class TreeNode(object):
    '''
    Adds some tree behavior to something that seems like a node in a tree
    '''

    def bfs(self, predicate, include_self=True):
        '''
        Performs a breadth first search, returning the first node that matches the predicate
        '''
        if include_self and predicate(self):
            return self
        for child in self:
            if predicate(child):
                return child
        for child in self:
            child_result = child.bfs(predicate)
            if child_result is not None:
                return child_result
        return None
    
    def dfs(self, predicate, include_self=True):
        '''
        Performs a depth first search, returning the first node that matches the predicate
        '''
        if include_self and predicate(self):
            return self
        for child in self:
            child_result = child.dfs(predicate)
            if child_result is not None:
                return child_result
        return None
    
    def dfs_do(self, expression, *args, **kwargs):
        '''
        Performs expression on each of the nodes (including this one) in a DFS manner
        '''
        expression(self, *args, **kwargs)
        for child in self:
            child.dfs_do(expression, *args, **kwargs)

    def find_first_ancestor(self, predicate, include_self=True):
        '''
        Performs a search up the ancestor chain, finding the first ancestor that matches
        the predicate
        '''
        if include_self and predicate(self):
            return self
        if self.getparent() is None:
            return None
        return self.getparent().find_first_ancestor(predicate)


class LocationChangedEvent(Event):
    
    name = 'location'
    
    def __init__(self, old_value, new_value):
        Event.__init__(self, LocationChangedEvent.name, synchronous=True, bubbles=True)
        self.old_value = old_value
        self.new_value = new_value
    
class RomElement(ElementBase, EventTarget, TreeNode):
    
    window = None
    
    def __str__(self):
        return "{0}({1})".format(self.tag, self.get(Attributes.Id))
    
    def get_id(self):
        return int(self.get(Attributes.Id))
    
    def get_bool(self, attr_name, default_value=False):
        value = self.get(attr_name)
        if value is None:
            return default_value
        else:
            return self.get(attr_name).lower() in ["true", "t", "yes", "1", "y"]
    
    def set(self, attr_name, attr_value):
        return ElementBase.set(self, attr_name, str(attr_value))
    
    def focus(self):
        self.dispatch_event(FocusRequestEvent())
        
    def getparent(self, *args, **kwargs):
        result = ElementBase.getparent(self, *args, **kwargs)
        if result is None:
            return RomElement.window
        else:
            return result

class TagProcessor(object):
    
    def __init__(self, tag_name):
        self.tag_name = tag_name
        
    def process(self, xml_element):
        if xml_element.tag == self.tag_name:
            self._do_process(xml_element)

    def _do_process(self, _):
        raise Exception("Override in child class")

class RamProcessor(TagProcessor):
    
    def __init__(self):
        TagProcessor.__init__(self, Tags.Ram)
    
    def _do_process(self, element):
        element.set(Attributes.Focusable, False)

class ContainerController(object):

    def __init__(self):
        self.remember_position = False
        self.__current_index = None
        self.navigation_theme = None

    def watch(self, element):
        self.__add_navigation_controller(element)
        element.add_event_listener(FocusEvent.focus_name, self.__on_focus)

    def navigate_forwards(self, element):
        if self.__current_index is None:
            if self.__has_real_children(element):
                self.__current_index = 0
            else:
                return
        else:
            if self.__current_index < (self.__num_real_children(element) - 1):
                self.__current_index += 1
            else:
                return
        self.__get_real_child(element, self.__current_index).focus()
    
    def navigate_backwards(self, element):
        if self.__current_index is None:
            return
        if self.__current_index == 0:
            return
        self.__current_index -= 1
        self.__get_real_child(element, self.__current_index).focus()
        
    def __get_real_child(self, element, index):
        real_index = 0
        for child in element:
            if child.tag == Tags.Title:
                continue
            if real_index == index:
                return child
            else:
                real_index += 1
        raise Exception("Index out of bounds: {0}".format(index))
        
    def __add_navigation_controller(self, element):
        if element.get(Attributes.NavigationTheme) is None:
            navcon = create_navigation_controller(NavigationTheme.HORIZONTAL, self)
        else:
            navcon = create_navigation_controller(element.get(Attributes.NavigationTheme), self)
        element.add_event_listener(KeyEvent.name, navcon.on_key)
        
    def __num_real_children(self, element):
        result = 0
        for child in element:
            if child.tag != Tags.Title:
                result += 1
        return result
        
    def __has_real_children(self, element):
        return self.__num_real_children(element) > 0
        
    def __get_title(self, element):
        for child in element:
            if child.tag == Tags.Title:
                return child
        
    def __get_component_to_focus_on_reset(self, element):
        title_element = self.__get_title(element) 
        if title_element is not None:
            return title_element
        if self.__current_index is None:
            if self.__has_real_children(element):
                self.__current_index = 0
            else:
                return None
        return self.__get_real_child(element, self.__current_index)
        
    def __on_focus(self, focus_event):
        if focus_event.event_phase == Event.AT_TARGET:
            if not self.remember_position:
                self.__current_index = None
            component = self.__get_component_to_focus_on_reset(focus_event.target)
            if component is not None:
                component.focus()
                focus_event.stop_propagation()

class ContainerProcessor(TagProcessor):
    
    def __init__(self):
        TagProcessor.__init__(self, Tags.Container)
    
    def _do_process(self, element):
        container_controller = ContainerController()
        container_controller.watch(element)
        
class IdPopulatingProcessor(object):
    
    def __init__(self):
        self.counter = 0
        
    def __get_next_id(self):
        result = self.counter
        self.counter += 1
        return result
        
    def process(self, element):
        element.set(Attributes.Id, str(self.__get_next_id()))
        
def create_processors_list():
    return [IdPopulatingProcessor(), ContainerProcessor(), RamProcessor()]

class Window(EventTarget):
    
    def __init__(self):
        EventTarget.__init__(self)
        #Singleton pattern!
        RomElement.window = self
        self.__location = None
        self.__root_element = None

    def getparent(self):
        return None
    
    def get_id(self):
        return "WINDOW"
        
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

