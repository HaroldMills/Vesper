"""Utility functions pertaining to Django forms."""


from vesper.singletons import archive, preference_manager


_DEFAULTS_PREFERENCE_NAME = 'form_defaults'


# TODO: Preference manager should perform preference type checking, not
# this module (and others).


def get_field_default(form_title, field_label, default):
    
    preferences = preference_manager.instance.preferences
    form_defaults = preferences.get(_DEFAULTS_PREFERENCE_NAME)
    
    if isinstance(form_defaults, dict):
        
        form_defaults = form_defaults.get(form_title)
        
        if isinstance(form_defaults, dict):
            return form_defaults.get(field_label, default)
        
    return default


def get_processor_choices(processor_type):
    archive_ = archive.instance
    detectors = archive_.get_visible_processors_of_type(processor_type)
    names = [archive_.get_processor_ui_name(d) for d in detectors]
    return [(n, n) for n in names]


def get_string_annotation_value_choices(annotation_name):
    archive_ = archive.instance
    specs = archive_.get_visible_string_annotation_ui_value_specs(
        annotation_name)
    return [(s, s) for s in specs]
