"""
Utility functions pertaining to plugins.

This module currently contains only private functions used by the
plugin infrastructure.
"""


def _set_plugin_type_attributes(plugin, plugin_type):
    
    """
    Sets the `type` and `interface` attributes of the specified plugin.
    
    This function is private to the plugin infrastructure, so its name
    begins with an underscore, even though it is called from modules
    other than this one.
    """
    
    plugin.type = plugin_type
    plugin.interface = _get_plugin_interface(plugin, plugin_type)
    
    
def _get_plugin_interface(plugin, plugin_type):
    
    interfaces = [
        i for i in plugin_type.supported_interfaces if issubclass(plugin, i)]
    
    interface_count = len(interfaces)
    
    if interface_count == 1:
        return interfaces[0]
    
    elif interface_count == 0:
        _handle_plugin_interface_error(
            f'Plugin is not a subclass of any supported '
            f'{plugin.type.name} plugin interface.')
        
    else:
        _handle_plugin_interface_error(
            f'Plugin is a subclass of more than one supported '
            f'{plugin.type.name} plugin interface.')
        
        
def _handle_plugin_interface_error(message):
    raise ValueError(
        f'{message} A plugin must be a subclass of exactly one of '
        f'the plugin interfaces supported by its plugin type.')
