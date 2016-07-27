"""Module containing `StationNameAliasesPreset` class."""


from vesper.util.yaml_preset import YamlPreset


class StationNameAliasesPreset(YamlPreset):
    
    """
    Preset that specifies station name aliases.
    
    The preset body is in YAML format and specifies a mapping from
    station names to lists of aliases.
    """
    
    type_name = 'Station Name Aliases'
        