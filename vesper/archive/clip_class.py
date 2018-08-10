"""Module containing class `ClipClass`."""


from vesper.util.named import Named


class ClipClass(Named):
    
    """
    Class of audio clips.
    
    A `ClipClass` represents a class of audio clip, such as a nocturnal
    flight call or a noise.
    
    A `ClipClass` has a *name* that comprises one or more dot-separated
    *components*. Examples of clip class names are `'Call'`, `'Noise'`,
    and `'Call.AMRE'`.
    """
    
    
    def __init__(self, name):
        super().__init__(name)
        self._name_components = tuple(name.split('.'))
        
        
    @property
    def name_components(self):
        return self._name_components
