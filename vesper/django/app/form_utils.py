"""Utility functions pertaining to Django forms."""


from vesper.singletons import preference_manager


_DEFAULTS_PREFERENCE_NAME = 'form_defaults'


_preferences = preference_manager.instance.preferences


# TODO: Preference manager should perform preference type checking, not
# this module (and others).


def get_field_default(form_title, field_label, default):
    
    form_defaults = _preferences.get(_DEFAULTS_PREFERENCE_NAME)
    
    if isinstance(form_defaults, dict):
        
        form_defaults = form_defaults.get(form_title)
        
        if isinstance(form_defaults, dict):
            return form_defaults.get(field_label, default)
        
    return default
