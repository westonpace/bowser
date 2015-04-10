'''
Created on Mar 24, 2015

@author: pace
'''
from xml.sax.handler import ContentHandler
import xml.sax
import inspect

class Node(object):
    '''
    Represents a node in a tree (although cycles are not explicitly prevented)
    '''

    def __init__(self, parent, children=None):
        self.parent = parent
        self.__children = children or []

    @property
    def children(self):
        '''
        The nodes children
        '''
        return self.__children
    
    def bfs(self, predicate, include_self=True):
        '''
        Performs a breadth first search, returning the first node that matches the predicate
        '''
        if include_self and predicate(self):
            return self
        for child in self.children:
            if predicate(child):
                return child
        for child in self.children:
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
        for child in self.children:
            child_result = child.dfs(predicate)
            if child_result is not None:
                return child_result
        return None
    
    def dfs_do(self, expression, *args, **kwargs):
        '''
        Performs expression on each of the nodes (including this one) in a DFS manner
        '''
        expression(self, *args, **kwargs)
        for child in self.children:
            child.dfs_do(expression, *args, **kwargs)

    def find_first_ancestor(self, predicate, include_self=True):
        '''
        Performs a search up the ancestor chain, finding the first ancestor that matches
        the predicate
        '''
        if include_self and predicate(self):
            return self
        if self.parent is None:
            return None
        return self.parent.find_first_ancestor(predicate)

class Element(Node):
    '''
    An element represents an element in an XML document.
    '''

    id_counter = 0
    
    @classmethod
    def __get_next_id_counter(cls):
        result = cls.id_counter
        cls.id_counter += 1
        return result

    def __init__(self, name, parent, attributes=None):
        Node.__init__(self, parent)
        self.__name = name
        self.__attributes = attributes or {}
        self.id = Element.__get_next_id_counter()

    @property
    def name(self):
        '''
        The name of the element (sometimes referred to as the tag name)
        '''
        return self.__name

    @property
    def attributes(self):
        '''
        The element's attributes, a map from string to string
        '''
        return self.__attributes
    
    def has_attribute(self, name):
        '''
        Returns True if the element has the specified attribute
        '''
        return name in self.__attributes
    
class XmlAttributeSetter(object):

    def __init__(self, attribute_name=None):
        self.attribute_name = attribute_name
        
    def __call__(self, func):
        if self.attribute_name is None:
            self.attribute_name = func.__name__
        func.xml_attribute_name = self.attribute_name
        return func
            
class XmlAttributes(object):

    def __init__(self, attribute_names):
        self.attribute_names = attribute_names
        
    def __call__(self, clazz):
        clazz.xml_attribute_names = self.attribute_names
        return clazz

class XmlElements(object):

    def __init__(self, element_names):
        self.element_names = element_names
        
    def __call__(self, clazz):
        clazz.xml_element_names = self.element_names
        return clazz

class XmlType(object):

    def __init__(self, tag_name):
        self.tag_name = tag_name
        
    def __call__(self, clazz):
        clazz.xml_tag_name = self.tag_name
        return clazz
        
class XmlParser(ContentHandler):
    
    def __init__(self, types, default_type, event_dispatcher):
        ContentHandler.__init__(self)
        self.tags_to_types = self.__initialize_type_map(types)
        self.default_type = default_type
        self.__event_dispatcher = event_dispatcher
        
    def __initialize_type_map(self, types):
        tags_to_types = {}
        for type_ in types:
            if not hasattr(type_, 'xml_tag_name'):
                raise Exception("Types given to XmlParser must be decorated with @XmlType")
            tags_to_types[type_.xml_tag_name] = type_
        return tags_to_types

    def parse(self, stream):
        builder = XmlParserBuilder(self.tags_to_types, self.default_type, self.__event_dispatcher)
        xml.sax.parse(stream, builder)
        return builder.result
        
class XmlParserBuilder(ContentHandler):
    
    def __init__(self, tags_to_types, default_type, event_dispatcher):
        ContentHandler.__init__(self)
        self.tags_to_types = tags_to_types
        self.default_type = default_type
        self.result = None
        self.__element_stack = list()
        self.__event_dispatcher = event_dispatcher
    
    def startDocument(self):
        ContentHandler.startDocument(self)

    def endDocument(self):
        ContentHandler.endDocument(self)

    def __get_top_of_stack(self):
        if len(self.__element_stack) > 0:
            return self.__element_stack[-1]
        else:
            return None

    def __instantiate_node(self, name):
        if name in self.tags_to_types:
            return self.tags_to_types[name](tag_name=name, parent_element=self.__get_top_of_stack())
        else:
            return self.default_type(tag_name=name, parent_element=self.__get_top_of_stack())

    def __is_setter_for_name(self, method, name):
        return hasattr(method, 'xml_attribute_name') and method.xml_attribute_name == name

    def __find_setter_method_on_node(self, node, name):
        for _, method in inspect.getmembers(node, predicate=inspect.ismethod):
            if self.__is_setter_for_name(method, name):
                return method
        return None

    def __set_attr_on_node(self, node, attr, value, is_listy):
        setter = self.__find_setter_method_on_node(node, attr)
        if setter is not None:
            setter(value)
        else:
            if is_listy:
                self.__set_list_attr_on_node(node, attr, value)
            else:
                setattr(node, attr, value)

    def __set_list_attr_on_node(self, node, attr, value):
        if hasattr(node, attr):
            old_value = getattr(node, attr)
            if old_value is None:
                setattr(node, attr, [value])
            else:
                old_value.append(value)
        else:
            setattr(node, attr, [value])

    def __set_attrs_on_node(self, node, attrs):
        for attr, value in iter(attrs.items()):
            self.__set_attr_on_node(node, attr, value, is_listy=False)

    def __sax_attrs_to_dict(self, attrs):
        return {name:attrs.getValue(name) for name in attrs.getNames()}

    def __build_node(self, name, attrs):
        attrs = self.__sax_attrs_to_dict(attrs)
        node = self.__instantiate_node(name)
        node.event_dispatcher = self.__event_dispatcher
        self.__set_attrs_on_node(node, attrs)
        return node

    def __append_node_to_element(self, node, parent):
        parent.children.append(node)
        self.__set_attr_on_node(parent, node.name, node, is_listy=True)

    def __append_node_to_current_element(self, node):
        parent = self.__get_top_of_stack()
        if parent is not None:
            self.__append_node_to_element(node, parent)
        else:
            self.result = node

    def __push_node_on_stack(self, node):
        self.__element_stack.append(node)

    def characters(self, content):
        ContentHandler.characters(self, content)
        stripped_content = content.strip()
        if len(stripped_content) > 0:
            current_node = self.__get_top_of_stack()
            if current_node is not None:
                current_node.text = stripped_content
        
    def startElement(self, name, attrs):
        ContentHandler.startElement(self, name, attrs)
        node = self.__build_node(name, attrs)
        self.__append_node_to_current_element(node)
        self.__push_node_on_stack(node)

    def __pop_node_off_stack(self):
        self.__element_stack.pop()

    def endElement(self, name):
        ContentHandler.endElement(self, name)
        self.__pop_node_off_stack()
    