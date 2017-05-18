"""Module containing class `ClipAlbumSettingsPreset`."""


from vesper.util.yaml_preset import YamlPreset
import vesper.util.case_utils as case_utils


class ClipAlbumSettingsPreset(YamlPreset):
    
    """
    Preset that specifies clip album settings.
    
    The preset body is YAML that specifies a mapping from setting names
    to setting values.
    """
    
    extension_name = 'Clip Album Settings'
    
    
    @property
    def camel_case_data(self):
        return case_utils.snake_keys_to_camel(self.data)
