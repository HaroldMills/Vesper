"""Module containing class `ClipGridSettingsPreset`."""


from vesper.util.yaml_preset import YamlPreset
import vesper.util.case_utils as case_utils


class ClipGridSettingsPreset(YamlPreset):
    
    """
    Preset that specifies clip grid settings.
    
    The preset body is YAML that specifies mapping from setting names
    to setting values.
    """
    
    extension_name = 'Clip Grid Settings'
    
    
    @property
    def camel_case_data(self):
        return case_utils.snake_to_camel(self.data)
