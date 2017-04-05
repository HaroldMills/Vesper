import logging
import os.path

import yaml


_PREFERENCE_FILE_NAME = 'Preferences.yaml'


class PreferenceManager:
    
    
    def __init__(self, preference_dir_path):
        self._preference_dir_path = preference_dir_path
        self.reload_preferences()
        
        
    def reload_preferences(self):
        self._preferences = _load_preferences(self._preference_dir_path)
        
        
    @property
    def preferences(self):
        return self._preferences
    
    
class _Preferences:
    
    
    def __init__(self, preferences):
        self._preferences = preferences
        
        
    def __getitem__(self, name):
        try:
            return _get_item(self._preferences, name)
        except:
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
            
            
def _load_preferences(dir_path):
    
    if not os.path.exists(dir_path):
        logging.error(
            'Preferences directory "{}" does not exist.'.format(dir_path))
        return {}
    
    if not os.path.isdir(dir_path):
        logging.error(
            'Path "{}" exists but is not a directory.'.format(dir_path))
        return {}

    path = os.path.join(dir_path, _PREFERENCE_FILE_NAME)
        
    try:
        with open(path, 'r') as file_:
            contents = file_.read()
    except Exception as e:
        logging.error(
            'Read of preference file "{}" failed with message: {}'.format(
                path, str(e)))
        return {}
    
    try:
        preferences = yaml.load(contents)
    except Exception as e:
        logging.error((
            'Load of YAML from preference file "{}" failed with '
            'message: {}').format(path, str(e)))
        return {}
    
    if preferences is None:
        # preferences file contains no data
        
        return {}
    
    elif not isinstance(preferences, dict):
        logging.error(
            'Preference file "{}" does not contain a YAML map.'.format(path))
        return {}
    
    return _Preferences(preferences)
