"""Module containing Vesper viewer preferences."""


from __future__ import print_function

import json
import os
import sys

from vesper.util.classification_commands_preset import \
    ClassificationCommandsPreset
from vesper.util.preset_manager import PresetManager
import vesper.util.vesper_path_utils as vesper_path_utils
        
            
_DEFAULT_PREFERENCES_FILE_NAME = 'Preferences.json'
_PRESETS_DIR_NAME = 'Presets'
_PRESET_TYPES = {ClassificationCommandsPreset}


_preferences = {}


def load_preferences(file_name=_DEFAULT_PREFERENCES_FILE_NAME):
    
    print('load_preferences')
    
    file_path = _get_preferences_file_path(file_name)
        
    global _preferences
    
    try:
        _preferences = _read_json_file(file_path)
        
    except Exception as e:
        f = 'An error occurred while loading application preferences: {:s}'
        _handle_error(f.format(str(e)))


def _get_preferences_file_path(file_name):
    app_data_dir_path = vesper_path_utils.get_path('App Data')
    return os.path.join(app_data_dir_path, file_name)


def _read_json_file(path):
    
    if not os.path.exists(path):
        raise ValueError('File "{:s}" does not exist.'.format(path))
    
    try:
        file_ = open(path, 'rU')
    except:
        raise IOError('Could not open file "{:s}".'.format(path))
    
    try:
        contents = json.load(file_)
    except ValueError:
        file_.close()
        raise ValueError('Could not load JSON file "{:s}".'.format(path))

    file_.close()
    return contents


def _handle_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)
    
    
def get(name, default=None):
    return _preferences.get(name, default)


def _create_preset_manager():
    app_data_dir_path = vesper_path_utils.get_path('App Data')
    presets_dir_path = os.path.join(app_data_dir_path, _PRESETS_DIR_NAME)
    return PresetManager(presets_dir_path, _PRESET_TYPES)
    
    
# TODO: Move this out of here. Presets should be handled by the preset
# manager, not by the preferences manager.
preset_manager = _create_preset_manager()

