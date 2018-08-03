"""Module containing class `DetectionSchedulePreset`."""


from vesper.util.yaml_preset import YamlPreset


class DetectionSchedulePreset(YamlPreset):
    
    """
    Preset that specifies a detection schedule.
    
    The preset body is YAML that specifies a detection schedule.
    """
    
    extension_name = 'Detection Schedule'
