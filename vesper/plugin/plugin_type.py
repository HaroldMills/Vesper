"""Module containing class `PluginType`."""


import logging
import pkg_resources

from vesper.plugin.plugin import Plugin


class PluginType(Plugin):
    
    """
    Abstract base class for plugin types.
    
    This class has all of the attributes required of plugin type
    classes (including those inherited from the `Plugin` class), but
    the attributes have `None` values instead of real ones. The
    attributes are provided mainly for the purpose of documentation.
    A subclass must provide real values for the attributes.
    
    The class also includes several methods that together load and
    provide access to plugins of the class's plugin type. These
    methods should suffice as is for many plugin types, but can
    be overridden when different functionality is needed.
    """
    
    
    entry_point_group_name = None
    """The setuptools entry point group name of this plugin type, a string."""
    
    supported_api_versions = None
    """The API versions supported for this plugin type, a tuple of strings."""
    
    
    def __init__(self):
        super().__init__()
        self._plugins_tuple = None
        self._plugins_dict = None
        
        
    def get_plugins(self):
        if self._plugins_tuple is None:
            self._init_plugins()
        return self._plugins_tuple
    
    
    def _init_plugins(self):
        self._plugins_tuple = self._load_plugins()
        self._plugins_dict = dict((p.name, p) for p in self._plugins_tuple)
        
        
    def _load_plugins(self):
        
        group_name = self.entry_point_group_name
        entry_points = list(pkg_resources.iter_entry_points(group_name))
        
        # Load plugins.
        plugins = [self._load_plugin(e) for e in entry_points]
        
        # Filter out `None` objects from failed loads.
        plugins = tuple(p for p in plugins if p is not None)
        
        return plugins
    
    
    def _load_plugin(self, entry_point):
        
        plugin_name = entry_point.name
        module_name = entry_point.module_name
        
        try:
            plugin_class = entry_point.load()
        
        except Exception as e:
            
            logging.warning(
                f'Load failed for plugin "{plugin_name}" of module '
                f'"{module_name}". Error message was: {str(e)}')
            
            return None
        
        try:
            self._validate_plugin(plugin_class)
            
        except Exception as e:
            
            logging.warning(
                f'Validation failed for plugin "{plugin_name}" of module '
                f'"{module_name}". Error message was: {str(e)}')
            
            return None

        return plugin_class


    def _validate_plugin(self, plugin):
        
        _check_class_attribute(plugin, 'name', str)
        
        # TODO: Make sure plugin class has the required attributes, and
        # that they have the correct types.
        pass
    
    
    def get_plugin(self, name):
        try:
            return self._plugins_dict[name]
        except KeyError:
            type_name = self.__class__.name.lower()
            raise ValueError(f'Unknown {type_name} plugin "{name}".')
    
        
def _check_class_attribute(cls, name, type_):
    
    try:
        value = getattr(cls, name)
        
    except AttributeError:
        raise TypeError(
            f'Plugin class "{cls.__name__}" is missing required '
            f'"{name}" class attribute.')
        
    if not isinstance(value, type_):
        raise TypeError(
            f'Attribute "{name}" of plugin class "{cls.__name__}" '
            f'does not have required type {type_.__name__}.')
