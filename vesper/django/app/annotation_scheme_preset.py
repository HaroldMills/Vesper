"""Module containing class `AnnotationSchemePreset`."""


from vesper.util.yaml_preset import YamlPreset


class AnnotationSchemePreset(YamlPreset):
    
    """
    Preset that specifies an annotation scheme.
    
    The preset body is YAML that specifies a sequence of mappings.
    Each mapping includes two items, an annotation name and the name
    of an Annotation Commands preset. Under the annotation scheme, the
    commands will be used to set the values of the named annotation.
    """
    
    extension_name = 'Annotation Scheme'
