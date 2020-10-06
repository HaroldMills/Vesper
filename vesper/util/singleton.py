"""Module containing class `Singleton`."""


# TODO: Get rid of this module and the `Singletons` module by putting
# singletons in the modules that define their classes. Allow programmers
# to use singletons, for example the plugin manager, by writing things
# like:
#
#     from vesper.plugin.plugin_manager import plugin_manager
#
#     detectors = plugin_manager.get_plugins('Detector')
#
# rather than:
#
#     from vesper.singletons import plugin_manager
#
#     detectors = plugin_manager.instance.get_plugins('Detector')


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
