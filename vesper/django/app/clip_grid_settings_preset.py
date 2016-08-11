"""Module containing class `ClipGridSettingsPreset`."""


from vesper.util.yaml_preset import YamlPreset


class ClipGridSettingsPreset(YamlPreset):
    
    """
    Preset that specifies clip grid settings.
    
    The preset body is YAML that specifies mapping from setting names
    to setting values.
    """
    
    extension_name = 'Clip Grid Settings'
