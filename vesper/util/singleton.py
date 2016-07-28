"""Module containing `Singleton` class."""


class Singleton:
    
    """
    Class an instance of which manages a single instance of another class.
    
    A `Singleton` instance creates a single instance of another class
    using a factory function specified at initialization. The instance
    is available to clients via the `instance` property. The instance
    is created lazily, which avoids import cycles that would otherwise
    occur in many situations.
    """
    
    
    def __init__(self, instance_factory):
        
        """
        Initializes this singleton.
        
        :Parameters:
            instance_factory : function
                function that takes no arguments an creates the instance
                managed by this singleton.
        """
        
        self._instance_factory = instance_factory
        self._instance = None
        
        
    @property
    def instance(self):
        if self._instance is None:
            self._instance = self._instance_factory()
        return self._instance
