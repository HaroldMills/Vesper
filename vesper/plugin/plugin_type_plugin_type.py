"""Module containing class `PluginTypePluginType`."""


from vesper.plugin.plugin_type_plugin_interface_1_0 import \
    PluginTypePluginInterface_1_0
import vesper.plugin.plugin_utils as plugin_utils


class PluginTypePluginType(PluginTypePluginInterface_1_0):
    
    """
    The plugin type of plugin types.
    
    This plugin type is also known as the *root plugin type*, since
    it is the root of the plugin type hierarchy.
    
    Note that this plugin is its own plugin type. This makes sense
    since it is intended to be the parent of all plugin types, and
    is itself a plugin type.
    """
    
    
    # Plugin attributes.
    name = 'Plugin Type'
    version = '1.0.0'
    description = 'The plugin type of plugin types.'
    author = 'Harold Mills'
    license = 'MIT'
    
    # Note that we cannot set the `type` attribute of this class here,
    # since the class to which we want to set it (i.e. this class) does
    # not yet exist (since we are still in the process of defining it).
    # Instead, we set the attribute (along with the `interface`
    # attribute) below, after the end of the class definition.
    
    # Plugin type attributes.
    entry_point_group_name = 'vesper.plugin_types'
    supported_interfaces = (PluginTypePluginInterface_1_0,)
    
    
    def _load_plugins(self):
        
        # Load plugin types other than this one.
        plugins = super()._load_plugins()
        
        return (self,) + plugins
    
    
    # TODO: Perform extra validation needed for plugin types.


# Set root plugin type `type` and `interface` attributes. See note
# above regarding why we do this here rather than within the
# `PluginTypePluginType` class.
plugin_utils._set_plugin_type_attributes(
    PluginTypePluginType, PluginTypePluginType)
