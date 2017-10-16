"""Module containing class `SettingsType`."""


from vesper.util.settings import Settings


# TODO: Add support for settings schemas that specify setting names and
# types and whether or not each setting is required.


class SettingsType:
    
    """
    The type of a software configuration settings object.
    
    A `SettingsType` has a *name* (a string) and a collection of
    default settings (a `Settings` object). The type can create
    a `Settings` object of its type from a data source that can be
    either a dictionary, a YAML string, or a YSML file. The created
    settings comprise the defaults updated with the settings specified
    in the data source.
    """
    
    
    def __init__(self, name, defaults):
        self.name = name
        self.defaults = defaults
        
        
    def create_settings_from_dict(self, d):
        settings = Settings.create_from_dict(d)
        return Settings(self.defaults, settings)
    
    
    def create_settings_from_yaml(self, s):
        settings = Settings.create_from_yaml(s)
        return Settings(self.defaults, settings)
        
        
    def create_settings_from_yaml_file(self, file_path):
        settings = Settings.create_from_yaml_file(file_path)
        return Settings(self.defaults, settings)
    