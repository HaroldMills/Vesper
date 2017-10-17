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
    
    path = os.path.join(dir_path, _PREFERENCE_FILE_NAME)
    defaults_message = 'Will use default preference values.'
    
    if not os.path.exists(path):
        logging.warning((
            'Could not find preferences file "{}". {}').format(
                path, defaults_message))
        return {}
        
    try:
        with open(path, 'r') as file_:
            contents = file_.read()
    except Exception as e:
        logging.error(
            'Read failed for preferences file "{}". {}'.format(
                path, defaults_message))
        return {}
    
    try:
        preferences = yaml.load(contents)
    except Exception as e:
        logging.error((
            'YAML load failed for preferences file "{}". {} YAML load error '
            'message was:\n{}').format(path, defaults_message, str(e)))
        return {}
    
    if preferences is None:
        # preferences file contains no data
        
        return {}
    
    elif not isinstance(preferences, dict):
        logging.error(
            'Preferences file "{}" does not contain a YAML map. {}'.format(
                path, defaults_message))
        return {}
    
    return _Preferences(preferences)
