import logging
import os.path

import vesper.util.yaml_utils as yaml_utils


_PREFERENCE_FILE_NAME = 'Preferences.yaml'

_DEFAULTS_MESSAGE =  'Will use default preference values.'
    

class PreferenceManager:
    
    
    @staticmethod
    def create_for_file(file_path):
        manager = PreferenceManager()
        manager.load_preferences_from_file(file_path)
        return manager


    @staticmethod
    def create_for_yaml(yaml):
        manager = PreferenceManager()
        manager.load_preferences_from_yaml(yaml)
        return manager


    def __init__(self):
        self._preferences = _Preferences()
        self._preference_file_path = None


    @property
    def preferences(self):
        return self._preferences
    
    
    def load_preferences_from_file(self, file_path):
        self._preferences = _load_preferences_from_file(file_path)
        self._preference_file_path = file_path
        
        
    def reload_preferences(self):
        if self._preference_file_path is not None:
            self.load_preferences_from_file(self._preference_file_path)
        
        
    def load_preferences_from_yaml(self, yaml):
        self._preferences = _load_preferences_from_yaml(yaml)
        self._preference_file_path = None
    
    
class _Preferences:
    
    
    def __init__(self, preferences=None):
        if preferences is None:
            preferences = dict()
        self._preferences = preferences
        
        
    def __len__(self):
        return len(self._preferences)
    
    
    def __getitem__(self, name):
        try:
            return _get_item(self._preferences, name)
        except Exception:
            raise KeyError(name)
        
        
    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default
        
        
    def __contains__(self, name):
        try:
            self[name]
        except KeyError:
            return False
        else:
            return True
        
        
def _get_item(preferences, name):
    
    parts = name.split('.', maxsplit=1)
    
    if len(parts) == 1:
        # name contains no dots
        
        return preferences[name]
    
    else:
        # name contains one or more dots
        
        return _get_item(preferences[parts[0]], parts[1])
            
            
def _load_preferences_from_file(file_path):
    
    if not os.path.exists(file_path):
        logging.warning(
            f'Preference file "{file_path}" does not exist. '
            f'{_DEFAULTS_MESSAGE}')
        return _Preferences()
        
    try:
        with open(file_path, 'r') as file_:
            yaml = file_.read()
    except Exception as e:
        logging.warning(
            f'Read failed for preference file "{file_path}". '
            f'{_DEFAULTS_MESSAGE}')
        return _Preferences()
    
    try:
        return _load_preferences_from_yaml_aux(yaml)
    except Exception as e:
        logging.warning(f'For preference file "{file_path}": {str(e)}')
        return _Preferences()


def _load_preferences_from_yaml(yaml):

    try:
        return _load_preferences_from_yaml_aux(yaml)
    except Exception as e:
        logging.warning(f'For preference string: {str(e)}')
        return _Preferences()


def _load_preferences_from_yaml_aux(yaml):

    try:
        preferences = yaml_utils.load(yaml)
    except Exception as e:
        raise Exception(
            f'Contents are not valid YAML. {_DEFAULTS_MESSAGE} '
            f'Error message was:\n{str(e)}')
    
    if preferences is None:
        # preference file contains no data
        
        return _Preferences()
    
    if not isinstance(preferences, dict):
        raise Exception(
            f'Contents are not a YAML mapping. {_DEFAULTS_MESSAGE}')
    
    return _Preferences(preferences)
