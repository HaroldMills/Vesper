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
    
    interface_version = None
    """
    The plugin interface version implemented by this plugin, a string.
    
    This attribute is typically set by plugin interface classes.
    A plugin interface class is an abstract subclass of the `Plugin`
    class that defines the methods and behavior of a plugin interface.
    A plugin interface class serves as a superclass for concrete
    plugin subclasses that implement the interface.
    """
