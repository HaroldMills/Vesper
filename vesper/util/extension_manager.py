"""Provides access to the extensions of a program."""


import importlib

import yaml


# Note that even though the `ExtensionManager` class is typically used as a
# singleton, we make it a class rather than a module to facilitate testing.
#
# Note also that rather than loading extensions in the `__init__` method,
# we defer the loading until the first call to the `get_extensions` method.
# Otherwise importing the `extension_manager` module would cause an import
# cycle, since the `extension_manager` would attempt to import extension
# modules before its import had completed, some of which would in turn
# attempt to import the `extension_manager` module. Deferring the extension
# module imports allows the import of the `extension_manager` module to
# complete before they begin.


# TODO: Discover extension points and extensions in plugins rather than
# specifying them in a YAML extensions specification. Note, however, that
# it might still be desirable to be able to specify different subsets of
# installed extensions to work with at different times, say for differen
# analysis projects.

# TODO: Use a hierarchical name space for plugins, extension points, and
# extensions?


class ExtensionManager(object):
    
    
    def __init__(self, extensions_spec):
        self._extensions_spec = extensions_spec
        self._extensions = None
        
        
    def get_extensions(self, extension_point_name):
        self._load_extensions_if_needed()
        extensions = self._extensions.get(extension_point_name, ())
        return dict((e.name, e) for e in extensions)
            
            
    def _load_extensions_if_needed(self):
        if self._extensions is None:
            spec = yaml.load(self._extensions_spec)
            self._extensions = dict(
                (type_name, _load_extension_classes(module_class_names))
                for type_name, module_class_names in spec.items())
    
    
def _load_extension_classes(module_class_names):
    return [_load_extension_class(name) for name in module_class_names]


def _load_extension_class(module_class_name):
    module_name, class_name = module_class_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
