"""Module containing class `ClipAlbumCommandsPreset`."""


from vesper.util.yaml_preset import YamlPreset
import vesper.util.case_utils as case_utils


class ClipAlbumCommandsPreset(YamlPreset):
    
    """
    Preset that specifies clip album keyboard commands.
    
    The preset body is YAML that specifies two mappings, one called
    `globals` that maps command interpreter global variable names
    to values, and another called `commands` that maps command
    names to command actions.
    """
    
    extension_name = 'Clip Album Commands'
    
    
    @property
    def camel_case_data(self):
        
        # We convert only the top-level dictionary keys to camel
        # case here since the global and command definitions of a
        # keyboard commands preset should remain snake case.
        
        return dict(_camelize_key(*i) for i in self.data.items())
        
        
def _camelize_key(key, value):
    return (case_utils.snake_to_camel(key), value)
