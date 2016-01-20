"""Module containing Vesper viewer preferences."""


from __future__ import print_function

import json
import os
import sys

import vesper.util.vesper_path_utils as vesper_path_utils
        
            
_DEFAULT_PREFERENCES_FILE_NAME = 'Preferences.json'


_preferences = {}


def load_preferences(file_name=_DEFAULT_PREFERENCES_FILE_NAME):
    
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

