"""Module containing `Preset` class."""


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
    of its superclass before doing anything else. For subclasses of the
    `Preset` class, this means invoking the
    
        def __init__(self, name):
            ...
            
    initializer of the `Named` class, since the `Preset` class does
    not define an initializer itself.
    """


    type_name = None
    """
    The name of this preset type.
    
    The name should be presentable in user interfaces, and is also the
    name of the subdirectory of the presets directory that contains
    presets of this type.
    """
