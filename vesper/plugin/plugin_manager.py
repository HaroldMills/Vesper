"""
Module containing the Vesper plugin manager.

The module contains both the `PluginManager` class, and the singleton
instance `plugin_manager` of that class. The instance is created when
this module is imported, and should be accessed by other modules via
the `plugin_manager` module attribute, e.g.:

    from vesper.plugin.plugin_manager import plugin_manager
"""


from vesper.plugin.plugin_type_plugin_type import PluginTypePluginType
from vesper.util.lazily_initialized import LazilyInitialized


class PluginManager(LazilyInitialized):
    
    """
    Plugin manager, which discovers, loads, and provides access to plugins.
    
    The plugin manager offers two public methods, `get_plugins`, which
    gets all plugins of a specified type, and `get_plugin` which gets
    a single plugin with a specified name and type.
    """
    
    # On (lazy) initialization, the plugin manager discovers and loads
    # all of the plugin types of the system, and creates a single
    # instance of each type. It uses those instances to satisfy requests
    # for plugins via the `get_plugins` and `get_plugin` methods.
    
    
    def _init(self):
        
        root_plugin_type_instance = PluginTypePluginType()
        
        # Get tuple of all plugin types.
        plugin_types = root_plugin_type_instance.get_plugins()
        
        # Create mapping from plugin type names to plugin type instances.
        # Exclude the root plugin type since we've already created an
        # instance of it. We will add it to the mapping below.
        self._plugin_type_instances = dict(
            (t.name, t()) for t in plugin_types
            if t is not PluginTypePluginType)
        
        # Add root plugin type to mapping.
        self._plugin_type_instances[PluginTypePluginType.name] = \
            root_plugin_type_instance
                
        
    @LazilyInitialized.initializer
    def get_plugins(self, type_name):
        plugin_type_instance = self._get_plugin_type_instance(type_name)
        return plugin_type_instance.get_plugins()
        
        
    def _get_plugin_type_instance(self, type_name):
        try:
            return self._plugin_type_instances[type_name]
        except Exception:
            raise ValueError(f'Unrecognized plugin type name "{type_name}".')
        
        
    @LazilyInitialized.initializer
    def get_plugin(self, type_name, plugin_name):
        plugin_type_instance = self._get_plugin_type_instance(type_name)
        return plugin_type_instance.get_plugin(plugin_name)


plugin_manager = PluginManager()
