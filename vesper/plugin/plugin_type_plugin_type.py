"""Module containing class `PluginTypePluginType`."""


from vesper.plugin.plugin_type_plugin_interface_1_0 import \
    PluginTypePluginInterface_1_0


class PluginTypePluginType(PluginTypePluginInterface_1_0):
    
    """
    The plugin type of plugin types.
    
    This plugin type is also known as the *root plugin type*.
    """
    
    
    # Plugin attributes. Note that the `type` attribute is set in the
    # `_load_plugins` method below rather than here since its value
    # (i.e. this class) does not yet exist here.
    name = 'Plugin Type'
    version = '1.0.0'
    description = 'The plugin type of plugin types.'
    author = 'Harold Mills'
    license = 'MIT'
    interface = PluginTypePluginInterface_1_0
    
    # Plugin type attributes.
    entry_point_group_name = 'vesper.plugin_types'
    supported_interfaces = (PluginTypePluginInterface_1_0,)
    
    
    def _load_plugins(self):
        
        # Set plugin type class attribute for this plugin type. See
        # note above regarding why we do this here rather than there.
        self.__class__.type = self.__class__
        
        # Load plugin types other than this one.
        plugins = super()._load_plugins()
        
        return (self,) + plugins
    
    
    # TODO: Perform extra validation needed for plugin types.
