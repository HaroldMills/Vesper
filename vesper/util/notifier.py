"""Module containing `Notifier` class."""


class Notifier:
    
    
    def __init__(self, client=None):
        self._client = client
        self._listeners = set()
        
        
    @property
    def client(self):
        return self._client
    
    
    def add_listener(self, listener):
        self._listeners.add(listener)
    
    
    def remove_listener(self, listener):
        self._listeners.discard(listener)
    
    
    def clear_listeners(self):
        self._listeners.clear()
    
    
    def notify_listeners(self, method_name, *args, **kwargs):
        
        for listener in self._listeners:
            
            method = getattr(listener, method_name)
            
            if self.client is None:
                method(*args, **kwargs)
            else:
                method(self.client, *args, **kwargs)
