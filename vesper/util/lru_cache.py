"""Module containing class `LruCache`."""


from collections import OrderedDict


class LruCache(OrderedDict):
    
    """
    Least-recently-used (LRU) cache.
    
    An LRU cache is an ordered mapping with a maximum size. Once the
    mapping has that size, it automatically deletes the least recently
    accessed (e.g. via the `__get__` or `__set__` method) item when an
    item with a new key is added to it.
    
    This class is based in part on the example "LRU" class of the
    documentation for the `OrderedDict` class of the `collections`
    module of the Python standard library.
    """


    def __init__(self, max_size=None, *args, **kwargs):
        
        # It is important initialize `self._max_size` before calling
        # `super().__init__` in case that method calls a method
        # (e.g. `__setitem__`) that uses it.
        self._max_size = max_size
        
        super().__init__(*args, **kwargs)
    
    
    @property
    def max_size(self):
        return self._max_size
    
    
    def __getitem__(self, key):
        
        # Get value for key.
        value = super().__getitem__(key)
        
        # Move item to end since it is now most recently used.
        self.move_to_end(key)
        
        return value
    

    def __setitem__(self, key, value):
        
        # Set value for key.
        super().__setitem__(key, value)
        
        # Move item to end since it is now most recently used.
        self.move_to_end(key)
        
        # Remove least recently used item if cache is full.
        max_size = self.max_size
        if max_size is not None and len(self) > max_size:
            oldest = next(iter(self))
            del self[oldest]
