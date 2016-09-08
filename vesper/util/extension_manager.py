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
# installed extensions to work with at different times, say for different
# analysis projects.

# TODO: Actually, it might be best to stick with an explicit extensions
# configuration. The extension manager can be initialized much more quickly
# if you know up front what and where all of the extensions are, and this
# has become newly important since we are running Vesper commands in their
# own processes. A new extension manager is created in each of these
# processes, and it is desirable that that creation be fast.

# TODO: In order to make starting the execution of Vesper commands faster,
# it would be helpful to be able to get a single extension by its
# extension point name and extension name, importing *exactly the modules
# needed by that extension* and no others. This need could be addressed
# by a new extension manager method `get_extension` that gets a single
# extension.

# TODO: Use a hierarchical name space for plugins, extension points, and
# extensions?


class ExtensionManager:
    
    
    def __init__(self, extensions_spec):
        self._extensions_spec = extensions_spec
        self._extensions = None
        
        
    def get_extensions(self, extension_point_name):
        self._load_extensions_if_needed()
        extensions = self._extensions.get(extension_point_name, ())
        return dict((e.extension_name, e) for e in extensions)
            
            
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
