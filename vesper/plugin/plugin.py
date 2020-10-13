"""Module containing class `Plugin`."""


class Plugin:
    
    """
    Abstract base class for plugins.
    
    This class has all of the attributes required of plugin classes,
    but the attributes have `None` values instead of real ones. The
    attributes are provided mainly for the purpose of documentation.
    A subclass must provide real values for the attributes.
    """
    
    
    name = None
    """The name of this plugin, a string."""
    
    version = None
    """The version of this plugin, a string."""
    
    description = None
    """Description of this plugin, a string."""
    
    author = None
    """The author of this plugin, a string."""
    
    license = None
    """The license of this plugin, a string."""
    
    type = None
    """
    The plugin type of this plugin, a subclass of the `PluginType` class.
    
    This attribute is set automatically when the plugin is loaded,
    according to the plugin's declared setuptools entry point group.
    """
    
    interface = None
    """
    The plugin interface implemented by this plugin, an abstract
    `Plugin` subclass.
    
    This attribute is set automatically when the plugin is loaded,
    according to the plugin interface that the plugin subclasses.
    Every plugin must be a subclass of exactly one of the supported
    plugin interfaces of its plugin type.
    """
