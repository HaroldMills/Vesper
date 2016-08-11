"""Module containing class `AnnotationCommandsPreset`."""


from vesper.util.yaml_preset import YamlPreset


class AnnotationCommandsPreset(YamlPreset):
    
    """
    Preset that specifies a set of annotation commands.
    
    The preset body is YAML that specifies a mapping from command
    names to command actions.
    """
    
    extension_name = 'Annotation Commands'
