"""Module containing class `DetectorPluginType`."""


from vesper.plugin.plugin_type import PluginType


class DetectorPluginType(PluginType):
    
    """Plugin type of detectors."""
    
    
    name = 'Detector'
    version = '1.0.0'
    description = 'Creates clips from a recording.'
    author = 'Harold Mills'
    license = 'MIT'
    plugin_type_name = 'Plugin Type'
    implemented_api_version = '1.0'
    
    entry_point_group_name = 'vesper.detectors'
    supported_api_versions = ('1.0',)
