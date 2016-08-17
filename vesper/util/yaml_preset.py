"""Module containing class `YamlPreset`."""


import yaml

from vesper.util.preset import Preset


class YamlPreset(Preset):
    
    
    """Abstract superclass for YAML presets."""
    
    
    def __init__(self, name, data):
        
        # Parse YAML into a Python data structure.
        try:
            data = yaml.load(data)
        except Exception as e:
            raise ValueError(str(e))
        
        super().__init__(name, data)
        