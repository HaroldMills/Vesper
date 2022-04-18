"""Utility functions pertaining to Django forms."""


from vesper.singleton.archive import archive
from vesper.singleton.preference_manager import preference_manager


_DEFAULTS_PREFERENCE_NAME = 'form_defaults'


def get_field_default(form_title, field_label, default):
    
    preferences = preference_manager.preferences
    form_defaults = preferences.get(_DEFAULTS_PREFERENCE_NAME)
    
    if isinstance(form_defaults, dict):
        
        form_defaults = form_defaults.get(form_title)
        
        if isinstance(form_defaults, dict):
            return form_defaults.get(field_label, default)
        
    return default


def get_processor_choices(processor_type):
    processors = archive.get_visible_processors_of_type(processor_type)
    names = [archive.get_processor_ui_name(p) for p in processors]
    return [(n, n) for n in names]


def get_string_annotation_value_choices(
        annotation_name, include_unannotated=True):
    specs = archive.get_visible_string_annotation_ui_value_specs(
        annotation_name, include_unannotated)
    return [(s, s) for s in specs]


def get_tag_choices(include_not_applicable=True):
    specs = archive.get_tag_specs(include_not_applicable)
    return [(s, s) for s in specs]


def get_preset_choices(preset_type, include_none=True):
    specs = archive.get_preset_specs(preset_type, include_none)
    return [(s, s) for s in specs]
