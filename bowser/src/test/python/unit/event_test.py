'''
Created on Mar 25, 2015

@author: Pace
'''
import unittest
from bowser.systems.event import EventTarget, EventDispatcher, Event
from bowser.xmlparse import Node

class EventsTest(unittest.TestCase):
    
    class TestNode(EventTarget, Node):
        
        def __init__(self, event_dispatcher, name, parent=None):
            EventTarget.__init__(self, event_dispatcher)
            Node.__init__(self, parent)
            self.name = name
            if parent is not None:
                parent.children.append(self)
    
    '''
    Builds a test tree of the form:
            
        A-1-i
           -ii
         -2
         -3-j
    '''
    def __build_test_tree(self, event_dispatcher):
        root = EventsTest.TestNode(event_dispatcher, "A")
        one = EventsTest.TestNode(event_dispatcher, "1", root)
        EventsTest.TestNode(event_dispatcher, "2", root)
        three = EventsTest.TestNode(event_dispatcher, "3", root)
        EventsTest.TestNode(event_dispatcher, "i", one)
        EventsTest.TestNode(event_dispatcher, "ii", one)
        EventsTest.TestNode(event_dispatcher, "j", three)
        return root
    
    def __get_node_by_name(self, root, name):
        return root.dfs(lambda x:x.name == name)
    
    class Trigger(object):
        
        def __init__(self):
            self.triggered = False
            
        def trigger(self, _):
            self.triggered = True
            
        def clear(self):
            self.triggered = False
    
    def test_bubbles(self):
        event_dispatcher = EventDispatcher()
        tree = self.__build_test_tree(event_dispatcher)
        trigger = EventsTest.Trigger()
        tree.add_event_listener('foo', trigger.trigger)
        
        bubbling_event = Event('foo', synchronous=True, bubbles=True)
        non_bubbling_event = Event('foo', synchronous=True, bubbles=False)
        
        tree.dispatch_event(bubbling_event)
        self.assertTrue(trigger.triggered, "Firing a bubbling event at the same point as the listener did not hit the listener")
        
        trigger.clear()
        tree.dispatch_event(non_bubbling_event)
        self.assertTrue(trigger.triggered, "Firing a non-bubbling event at the same point as the listener did not hit the listener")
        
        trigger.clear()
        leaf = self.__get_node_by_name(tree, 'ii')
        leaf.dispatch_event(bubbling_event)
        self.assertTrue(trigger.triggered, "Firing a bubbling event at a leaf did not hit a listener at the root")
        
        trigger.clear()
        leaf.dispatch_event(non_bubbling_event)
        self.assertFalse(trigger.triggered, "Firing a non-bubbling event at a leaf hit a listener at the root")
        
        tree.remove_event_listener('foo', trigger.trigger)
        leaf.add_event_listener('foo', trigger.trigger)
        
        leaf2 = self.__get_node_by_name(tree, 'i')
        leaf2.dispatch_event(bubbling_event)
        self.assertFalse(trigger.triggered, "Firing a bubbling event hit a listener on a sibling")
        
        tree.dispatch_event(bubbling_event)
        self.assertFalse(trigger.triggered, "Firing a bubbling event on the root hit a listener on the leaf")
        
    def test_capture(self):
        event_dispatcher = EventDispatcher()
        tree = self.__build_test_tree(event_dispatcher)
        trigger = EventsTest.Trigger()
        tree.add_event_listener('foo', trigger.trigger, use_capture=False)
        
        self.behaved_correctly = True
        def ensure_trigger_unfired(_):
            if trigger.triggered:
                self.behaved_correctly = False
                
        tree.add_event_listener('foo', ensure_trigger_unfired, use_capture=True)
        
        #Should ensure that capture phase occurs before target phase
        tree.dispatch_event(Event('foo'))
        
        self.assertTrue(self.behaved_correctly, "The use_capture=False listener on a node got triggered before the use_capture=True listener")
        self.assertTrue(trigger.triggered, "The use_capture=True listener somehow prevented the use_capture=True listener even though it did not stop propagation")
        
        tree.remove_event_listener('foo', trigger.trigger, use_capture=False)
        #Should ensure capture order is root-to-leaf and not vice-versa
        leaf = self.__get_node_by_name(tree, 'ii')
        leaf.add_event_listener('foo', trigger.trigger, use_capture=True)
        
        trigger.clear()
        leaf.dispatch_event(Event('foo'))
        self.assertTrue(self.behaved_correctly, "The capture listener on a leaf node fired before the capture listener on the root node")
        self.assertTrue(trigger.triggered, "The capture listener on a root node prevented a capture listener on the leaf node even though it didn't stop propagation")
        
        #Allow root capture listener to stop propagation
        trigger.clear()
        def stop_prop(event):
            event.stop_propagation()
        tree.add_event_listener('foo', stop_prop, use_capture=True)
        
        leaf.dispatch_event(Event('foo'))
        self.assertFalse(trigger.triggered, "The leaf listener got to run even though a capture listener at the root stopped propagation")
