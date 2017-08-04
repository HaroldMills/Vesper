"""Utility functions pertaining to Django forms."""


from vesper.singletons import preference_manager


_preferences = preference_manager.instance.preferences


def get_field_default(form_name, field_name, default):
    defaults_name = form_name + '_defaults'
    defaults = _preferences.get(defaults_name, {})
    return defaults.get(field_name, default)
