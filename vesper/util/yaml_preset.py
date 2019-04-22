"""Module containing class `YamlPreset`."""


from vesper.util.preset import Preset
import vesper.util.yaml_utils as yaml_utils


class YamlPreset(Preset):
    
    
    """Abstract superclass for YAML presets."""
    
    
    def __init__(self, name, data):
        
        # Parse YAML into a Python data structure.
        try:
            data = yaml_utils.load(data)
        except Exception as e:
            raise ValueError(str(e))
        
        super().__init__(name, data)
