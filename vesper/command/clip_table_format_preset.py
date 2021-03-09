"""Module containing class `ClipTableFormatPreset`."""


from vesper.util.yaml_preset import YamlPreset


class ClipTableFormatPreset(YamlPreset):
    
    """
    Preset that specifies a clip table format.
    
    The preset body is YAML that specifies a table format.
    """
    
    extension_name = 'Clip Table Format'
