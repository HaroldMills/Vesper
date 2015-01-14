"""
Notifier class, an instance of which maintains a set of listeners
that it invokes on request.
"""


class Notifier(object):
    
    
    def __init__(self):
        self._listeners = set()
        
        
    def add_listener(self, listener):
        self._listeners.add(listener)
        
        
    def remove_listener(self, listener):
        try:
            self._listeners.remove(listener)
        except KeyError:
            pass
        
        
    def clear_listeners(self):
        self._listeners.clear()
        
        
    def notify_listeners(self, *args, **kwargs):
        for listener in self._listeners:
            listener(*args, **kwargs)
