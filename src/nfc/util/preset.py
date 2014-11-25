"""Module containing `Preset` class."""


class Preset(object):
    
    
    type_name = None
    """
    The name of this preset type.
    
    The name should be presentable in user interfaces, and is also the
    name of the subdirectory of the presets directory that contains
    presets of this type.
    """


    def __init__(self, name):
        
        """
        Initializes this preset with the specified name.
        
        Each subclass should define an initializer of the form:
        
            def __init__(self, name, data):
                ...
                
        for the preset manager to use to create presets of this type.
        The initializer accepts a preset name and serialized preset data,
        for example the contents of a preset file. The subclass initializer
        should invoke its superclass initializer (i.e. this initializer)
        before doing anything else.
        """
        
        super(Preset, self).__init__()
        self._name = name
        
        
    @property
    def name(self):
        return self._name
