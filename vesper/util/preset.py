"""Module containing class `Preset`."""


from vesper.util.named import Named


class Preset(Named):
    
    """
    Preset parent class.
    
    A *preset* is a collection of logically related configuration data,
    for example for user interface or algorithm configuration. A preset
    is of a particular *preset type*, according to the type of information
    it contains. For example, a system may offer preset types for the
    configuration of different parts of its user interface, or for the
    configuration of different parametric algorithms. A preset type is
    implemented in Python as a subclass of the `Preset` class, and
    presets of that type are instances of the class.
    
    Presets are managed by a *preset manager*, which loads presets from
    a persistent store and provides them to clients upon request. The
    preset manager requires that each preset class define an initializer
    of the form
    
        def __init__(self, name, data):
            ...
            
    which the manager uses to create presets. The initializer accepts a
    preset name and serialized preset data, both of which are obtained
    by the preset manager from the persistent store.
    
    The initializer of a preset class should always invoke the initializer
    of its superclass before doing anything else.
    """


    extension_name = None
    """
    The extension name of this preset type.
    
    A preset type is an extension, and thus must have an extension name.
    The name should be capitalized and describe the contents of the preset,
    for example "Annotation Commands" or "Annotation Scheme". The name is
    presented in user interfaces as the name of a preset type, and is also
    the name of the directory that contains presets of this type.
    """
    
    
    def __init__(self, name):
        super().__init__(name)
