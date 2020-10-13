"""Module containing class `PluginType`."""


from vesper.plugin.plugin import Plugin


class PluginType(Plugin):
    
    """
    Abstract base class for plugin types.
    
    This class has all of the attributes required of plugin type
    classes (including those inherited from the `Plugin` class), but
    the attributes have `None` values instead of real ones. The
    attributes are provided mainly for the purpose of documentation.
    A subclass must provide real values for the attributes.
    """
    
    
    entry_point_group_name = None
    """The setuptools entry point group name of this plugin type, a string."""
    
    supported_interfaces = None
    """
    The plugin interfaces supported for this plugin type, a tuple of
    abstract `Plugin` subclasses. Every plugin of this type must
    subclass exactly one of these interfaces.
    """
