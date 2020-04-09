"""Module containing class `Settings`."""


from vesper.util.bunch import Bunch
import vesper.util.os_utils as os_utils
import vesper.util.yaml_utils as yaml_utils


class Settings(Bunch):
    
    """
    Collection of software configuration settings.
    
    A *setting* has a *name* and a *value*. The name must be a Python
    identifier. The value must be `None` or a boolean, integer, float,
    string, list, or `Settings` object. A setting contained in a
    `Settings` object is accessed as an attribute of the object.
    For example, a setting `x` of a settings object `s` is accessed
    as `s.x`.
    """
    
    @staticmethod
    def create_from_dict(d):
        
        """Creates a settings object from a dictionary."""
        
        if not isinstance(d, dict):
            raise TypeError(
                'Settings data must be a dictionary, not a {}.'.format(
                    d.__class__.__name__))
        
        d = dict(
            (k, Settings._create_from_dict_aux(v))
            for k, v in d.items())
        
        return Settings(**d)


    @staticmethod
    def _create_from_dict_aux(v):
        if isinstance(v, dict):
            return Settings.create_from_dict(v)
        elif isinstance(v, list):
            return [Settings._create_from_dict_aux(i) for i in v]
        else:
            return v
    
    
    @staticmethod
    def create_from_yaml(s):
    
        """Creates a settings object from a YAML string."""
        
        try:
            d = yaml_utils.load(s)
            
        except Exception as e:
            raise ValueError(
                'YAML parse failed. Error message was:\n{}'.format(str(e)))
        
        if d is None:
            d = dict()
            
        elif not isinstance(d, dict):
            raise ValueError('Settings must be a YAML mapping.')
        
        return Settings.create_from_dict(d)
    
    
    @staticmethod
    def create_from_yaml_file(file_path):
        
        """Creates a settings object from a YAML file."""
        
        s = os_utils.read_file(file_path)
        return Settings.create_from_yaml(s)
