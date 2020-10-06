"""Module containing class `LazilyInitialized`."""


class LazilyInitialized:
    
    """
    Superclass of objects that are initialized lazily.
    
    Some or all of the initialization of a lazily initialized object is
    deferred until after its `__init__` method is called.
    
    Lazy initialization can be used to:
    
    * Increase program startup speed.
    
    * Avoid incurring the cost of initialization for an object until it
      is actually used, saving that cost for objects that are never used.
    """
    
    
    @staticmethod
    def initter(method):
        
        """
        Decorator for `LazilyInitialized` instance methods that initializes
        an object if needed before invoking the decorated method on it.
        """
        
        def wrapper(self, *args, **kwargs):
            
            if not self._initialized:
                self._init()
                self._initialized = True
                
            return method(self, *args, **kwargs)
        
        return wrapper
    
    
    def __init__(self):
        self._initialized = False
        
        
    def _init(self):
        
        """
        Initializes a `LazilyInitialized` object.
        
        The default implementation of this method does nothing.
        Subclasses can override the method to perform their initialization.
        An indirect `LazilyInitialized` subclass should always call
        `super()._init` from its `_init` method.
        """
        
        pass
