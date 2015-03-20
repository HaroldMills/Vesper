"""Module containing Vesper viewer preferences."""


from __future__ import print_function

import json
import os
import sys

from vesper.util.classification_commands_preset import \
    ClassificationCommandsPreset
from vesper.util.preset_manager import PresetManager
        
            
_PREFS_DIR_NAME = 'Vesper'
_PREFS_VAR_NAME = 'VESPER_PREFS'
_PREFS_FILE_NAME = 'Preferences.json'
_PRESETS_DIR_NAME = 'Presets'
_PRESET_TYPES = {ClassificationCommandsPreset}


def _load_preferences():
    
    prefs_dir_path = _get_prefs_dir_path()
    prefs_file_path = os.path.join(prefs_dir_path, _PREFS_FILE_NAME)
    
    try:
        return _read_json_file(prefs_file_path)
    except Exception as e:
        f = 'An error occurred while loading application preferences: {:s}'
        _handle_error(f.format(str(e)))


# TODO: Put this in a JSON utility module?
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


def _get_prefs_dir_path():
    home_dir_path = os.path.expanduser('~')
    default_prefs_dir_path = os.path.join(home_dir_path, _PREFS_DIR_NAME)
    return os.environ.get(_PREFS_VAR_NAME, default_prefs_dir_path)


def _handle_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)
    
    
def _create_preset_manager():
    prefs_dir_path = _get_prefs_dir_path()
    presets_dir_path = os.path.join(prefs_dir_path, _PRESETS_DIR_NAME)
    return PresetManager(presets_dir_path, _PRESET_TYPES)
    
    
preferences = _load_preferences()
preset_manager = _create_preset_manager()
