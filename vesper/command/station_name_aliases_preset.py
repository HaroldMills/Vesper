"""Module containing class `StationNameAliasesPreset`."""


from vesper.util.yaml_preset import YamlPreset


class StationNameAliasesPreset(YamlPreset):
    
    """
    Preset that specifies station name aliases.
    
    The preset body is YAML that specifies a mapping from station names
    to lists of aliases.
    """
    
    extension_name = 'Station Name Aliases'
    