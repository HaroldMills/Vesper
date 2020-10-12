"""Module containing class `RootPluginType`."""


from vesper.plugin.plugin_type import PluginType


class RootPluginType(PluginType):
    
    """
    The plugin type of plugin types.
    
    By convention, the name of a class representing a plugin type has
    the form <plugin name>PluginType, where <plugin name> is the camel
    case version of the name of the plugin type (i.e. the value of the
    `name` attribute of the class representing the plugin type). For
    example, for a plugin type named "File Format" the plugin type
    class would have the name `DetectorPluginType`. According to this
    convention, the name of this class should be `PluginTypePluginType`,
    since the name of the plugin type it represents is "Plugin Type".
    That's a rather awkward name, though, so we have broken with
    conventionand called the class `RootPluginType` instead, which we
    think makes more sense.
    """
    
    
    # Plugin attributes.
    name = 'Plugin Type'
    version = '1.0.0'
    description = 'The plugin type of plugin types.'
    author = 'Harold Mills'
    license = 'MIT'
    
    # Plugin type attributes.
    entry_point_group_name = 'vesper.plugin_types'
    supported_interfaces = ('1.0',)
    
    
    def _load_plugins(self):
        plugins = super()._load_plugins()
        return (self,) + plugins
    
    
    # TODO: Perform extra validation needed for plugin types.
