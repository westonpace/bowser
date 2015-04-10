'''
Created on Mar 29, 2015

@author: Pace
'''
class UninjectedDependency(object):
    
    def __init__(self, name):
        self.name = name
        
    def __getattr__(self, name):
        raise AttributeError("Dependency {0} has not been injected.".format(name))

class InjectionTarget(object):
    
    def __init__(self):
        self.__things_to_inject = set()
        
    def _inject(self, name):
        self.__things_to_inject.add(name)
        return UninjectedDependency(name)
    
    def supply_dependency(self, name, value):
        if name in self.__things_to_inject:
            setattr(self, name, value)
        