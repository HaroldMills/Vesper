"""Module containing class `Preset`."""


from vesper.util.named import Named


class Preset(Named):
    
    """
    Preset parent class.
    
    A *preset* is a collection of logically related data, for example
    user interface or algorithm settings. A preset is of a particular
    *preset type*, according to the type of data it contains. A preset
    type is implemented in Python as a subclass of the `Preset` class,
    and all presets of a type are instances of its class.
    
    The presets of an application are organized in a tree-structured
    hierarchy called the *preset tree*. Each leaf node of the tree
    corresponds to a preset, and each internal node corresponds to a
    *preset group* containing the presets of the subtree rooted at
    that node. The root of the preset tree is the group of all
    presets. There is exactly one child of the root for each preset
    type, and its preset group comprises all presets of that type.
    There may be additional levels of internal nodes in the preset
    tree, depending on the application.
    
    Each preset and preset group, and correspondingly each node of
    the preset tree, has a string *name*. The root node of the tree
    is named "Presets", and the names of its children are the names
    of the corresponding preset types. Internal nodes at other levels
    of the tree have names assigned some other way. For example, for
    a preset tree that persists in a file system, with a file system
    directory for each preset group, the names of internal nodes
    might be the names of those directories. The name of each leaf
    node is the name of the corresponding preset.
    
    Each preset and preset group also has a *path*, the tuple of
    names of the non-root preset tree nodes visited when traversing
    the tree from the root node to the node corresponding to the
    preset or group.

    For example, consider the following preset tree, where we
    represent hierarchy with indentation, internal tree nodes have
    alphabetic names, and presets have numeric names:
    
        Presets
            A
                1
                X
                    2
                    3
            B
                4
                5
    
    In this hierarchy, "A" and "B" are preset type names and "X" is
    the name of a preset group containing presets "2" and "3", a
    proper subset of preset group "A". "1", "2", and "3" are names
    of presets of type A, and "4" and "5" are names of presets of
    type B. The paths of the four groups of the hierarchy are:
    
        Presets: ()
        A: ("A",)
        B: ("B",)
        X: ("A", "X")
        
    and the paths of the five presets are:
    
        1: ("A", "1")
        2: ("A", "X", "2")
        3: ("A", "X", "3")
        4: ("B", "4")
        5: ("B", "5")
        
    Presets are managed by a *preset manager* that loads presets from
    a persistent store and provides them to clients upon request. The
    preset manager requires that each preset class define an initializer
    of the form
    
        def __init__(self, path, data):
            ...
            
    which the manager uses to create presets. The initializer accepts a
    preset path and serialized preset data, both of which are obtained
    by the preset manager from the persistent store.
    
    The initializer of a preset class should always invoke the initializer
    of its superclass.
    
    When preset data include key/value pairs where the keys are intended
    to function as programming language identifiers (when the keys are
    setting names, for example), the identifiers should be written in
    snake case. The `camel_case_data` property of a preset gets the preset
    data with such identifiers translated to camel case. Subclasses that
    need to perform such translation should define their own
    `camel_case_data` property. The default implementation of the
    property returns the preset data with no translation.
    """


    extension_name = None
    """
    The extension name of this preset type.
    
    A preset type is an extension, and thus must have an extension name.
    The name should be capitalized and describe the contents of the preset,
    for example "Clip Album Settings" or "Spectrogram Settings". The name
    is presented in user interfaces as the name of a preset type.
    """
    
    
    def __init__(self, path, data):
        super().__init__(path[-1])
        self._path = path
        self._data = data
        
        
    @property
    def path(self):
        return self._path
    
    
    @property
    def data(self):
        return self._data
    
    
    @property
    def camel_case_data(self):
        return self.data
