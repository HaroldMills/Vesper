"""Module containing class `LazilyInitialized`."""


class LazilyInitialized:
    
    """
    Superclass of objects that are initialized lazily.
    
    Some or all of the initialization of a lazily initialized object is
    deferred from its `__init__` method until other methods are called.
    
    Lazy initialization can be used to increase program startup speed
    by deferring some initialization, and to save resources by avoiding
    initialization of program components that might never be used.
    """
    
    
    @staticmethod
    def initializer(method):
        
        """
        Decorator for subclass instance methods that initialize if needed
        before doing anything else.
        
        An instance method that needs to ensure that the object it's called
        on is initialized can either be decorated with this decorator or it
        can call `self._initialize_if_needed` directly before doing anything
        else.
        """
        
        def wrapper(self, *args, **kwargs):
            self._initialize_if_needed()
            return method(self, *args, **kwargs)
        
        return wrapper
    
    
    def __init__(self):
        self._initialized = False
        
        
    def _initialize_if_needed(self):
        
        """
        Initializes this object if needed by calling its `_init` method.
        """
        
        if not self._initialized:
            self._init()
            self._initialized = True
    
    
    def _init(self):
        
        """
        Initializes a `LazilyInitialized` object.
        
        The default implementation of this method does nothing.
        Subclasses can override the method to perform their initialization.
        Any indirect `LazilyInitialized` subclass (i.e. one that is not
        a direct subclass of `LazyInitialized`) must call `super()._init`
        from its `_init` method.
        """
        
        pass
    
    
    # TODO: Add `reinitialize` method? That method would not necessarily
    # be supported by a subclass, in which case according to the Python 3.9
    # documentation for `NotImplementedError` the subclass should set the
    # method to `None`.
