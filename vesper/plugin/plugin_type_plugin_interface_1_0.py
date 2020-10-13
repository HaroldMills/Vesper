"""Module containing class `PluginTypePluginInterface_1_0`."""


import logging
import pkg_resources

from vesper.plugin.plugin_type import PluginType
import vesper.plugin.plugin_utils as plugin_utils


class PluginTypePluginInterface_1_0(PluginType):
    
    """
    Abstract superclass for plugin types that implement version 1.0
    of the plugin type plugin interface.
    
    At a minimum, a subclass of this class must specify all of the
    class attributes defined for the `Plugin` and `PluginType` classes,
    except for the `type` attribute (which is set automatically) and
    the `interface_version` attribute (which is set by this class).
    
    The class includes several methods that together load and provide
    access to plugins of the class's plugin type. These methods should
    suffice to implement many plugin types, but can be overridden when
    different functionality is needed. Of the included methods, a
    subclass is probably most likely to want to override the
    `_validate_plugin` method.
    """


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
        
        # Load plugin class.
        try:
            plugin = entry_point.load()
        except Exception as e:
            self._handle_load_failure('Load', plugin_name, module_name, e)
            return None
        
        # Set `type` and `interface` plugin class attributes.
        try:
            plugin_utils._set_plugin_type_attributes(plugin, self.__class__)
        except Exception as e:
            self._handle_load_failure(
                'Validation', plugin_name, module_name, e)
            return None
        
        # Validate.
        try:
            self._validate_plugin(plugin)
        except Exception as e:
            self._handle_load_failure(
                'Validation', plugin_name, module_name, e)
            return None
        
        return plugin
    
    
    def _handle_load_failure(
            self, operation, plugin_name, module_name, exception):
        
        logging.warning(
            f'{operation} failed for plugin "{plugin_name}" of module '
            f'"{module_name}". Error message was: {str(exception)}')
            

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
