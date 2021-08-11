from pathlib import Path
import logging
import os.path

import vesper.util.yaml_utils as yaml_utils


_PREFERENCE_FILE_NAME = 'Preferences.yaml'


class PreferenceManager:
    
    
    def __init__(self, preference_file_path):
        self._load_preferences(preference_file_path)
        self._stack = []
        
        
    def _load_preferences(self, preference_file_path):
        self._preferences = _load_preferences(preference_file_path)
        self._preference_file_path = preference_file_path
        
        
    def reload_preferences(self):
        self._load_preferences(self._preference_file_path)
        
        
    @property
    def preferences(self):
        return self._preferences
    
    
    def _push_test_module_preferences(self, test_module_file_path):
        
        """
        Pushes preferences for a unit test module.
        
        Some unit test modules require special preference values. Such
        a module can push preference values using this function as part
        of its setup, and pop them using the `_pop_test_preferences`
        method as part of its teardown.
        """
        
        test_module_file_path = Path(test_module_file_path)
        test_module_dir_path = test_module_file_path.parent
        test_module_name = test_module_file_path.stem
        preference_file_path = \
            test_module_dir_path / 'data' / test_module_name / \
            _PREFERENCE_FILE_NAME
            
        # Push current preferences onto stack.
        self._stack.append((self._preference_file_path, self._preferences))
        
        # Load test preferences.
        self._load_preferences(preference_file_path)
        
        
    def _pop_test_preferences(self):
        
        """Pops test preferences."""
        
        self._preference_file_path, self._preferences = self._stack.pop()
    
    
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
            
            
def _load_preferences(file_path):
    
    defaults_message = 'Will use default preference values.'
    
    if not os.path.exists(file_path):
        logging.warning(
            f'Preference file "{file_path}" does not exist. '
            f'{defaults_message}')
        return _Preferences()
        
    try:
        with open(file_path, 'r') as file_:
            contents = file_.read()
    except Exception as e:
        logging.warning(
            f'Read failed for preference file "{file_path}". '
            f'{defaults_message}')
        return _Preferences()
    
    try:
        preferences = yaml_utils.load(contents)
    except Exception as e:
        logging.warning(
            f'YAML load failed for preference file "{file_path}". '
            f'{defaults_message} YAML load error message was:\n{str(e)}')
        return _Preferences()
    
    if preferences is None:
        # preference file contains no data
        
        return _Preferences()
    
    elif not isinstance(preferences, dict):
        logging.warning(
            f'Preference file "{file_path}" does not contain a YAML mapping. '
            f'{defaults_message}')
        return _Preferences()
    
    return _Preferences(preferences)
