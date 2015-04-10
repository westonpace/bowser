'''
Created on Mar 25, 2015

@author: Pace
'''
import logging

from bowser.systems.focus import FocusEvent


class RenderingSystem(object):
    
    def __init__(self, focus_tree_root, audio_system):
        self.logger = logging.getLogger(__name__)
        focus_tree_root.add_event_listener(FocusEvent.focus_name, self.__on_focus)
        self.text_channel = audio_system.tts_channel
        
    def __add_texts_to_list(self, node, texts):
        if node.text is not None:
            texts.append(node.text)
        
    def __build_texts_to_render(self, target):
        texts_to_render = []
        target.dfs_do(self.__add_texts_to_list, texts_to_render)
        return texts_to_render
        
    def __render(self, target):
        self.logger.debug("Rendering target: %s", target)
        self.text_channel.interrupt()
        text_to_render = ' '.join(self.__build_texts_to_render(target))
        self.text_channel.queue(text_to_render)
        
    def __on_focus(self, focus_event):
        self.__render(focus_event.target)
        