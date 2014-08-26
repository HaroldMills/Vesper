"""Module containing NFC Viewer preferences."""


from __future__ import print_function

import json
import os
import sys

import nfc.util.classification_command_set_utils as command_set_utils
        
            
_PREFS_DIR_NAME = 'NFC'
_PREFS_VAR_NAME = 'NFC_PREFS'
_PREFS_FILE_NAME = 'Preferences.json'
_PRESETS_DIR_NAME = 'Presets'
_COMMAND_SETS_DIR_NAME = 'Classification Command Sets'
_TEXT_FILE_NAME_EXTENSION = '.txt'


def _load_preferences():
    
    prefs_dir_path = _get_prefs_dir_path()
    prefs_file_path = os.path.join(prefs_dir_path, _PREFS_FILE_NAME)
    
    try:
        file_ = open(prefs_file_path, 'rU')
    except:
        f = 'Could not open preferences file "{:s}".'
        _handle_error(f.format(prefs_file_path))
    
    try:
        prefs = json.load(file_)
    except ValueError:
        file_.close()
        f = 'Could not parse preferences file "{:s}".'
        _handle_error(f.format(prefs_file_path))

    file_.close()
        
    try:
        # TODO: Implement preset manager and get command sets from it?
        prefs['clipsWindow.commandSets'] = \
            _parse_command_sets(prefs_dir_path)
    except ValueError as e:
        _handle_error(str(e))

    return prefs


def _get_prefs_dir_path():
    home_dir_path = os.path.expanduser('~')
    default_prefs_dir_path = os.path.join(home_dir_path, _PREFS_DIR_NAME)
    return os.environ.get(_PREFS_VAR_NAME, default_prefs_dir_path)


def _handle_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)
    
    
def _parse_command_sets(prefs_dir_path):
    
    command_sets = {}
    dir_path = os.path.join(
        prefs_dir_path, _PRESETS_DIR_NAME, _COMMAND_SETS_DIR_NAME)
    
    # TODO: Complain if preset directory does not exist.
    
    for _, _, file_names in os.walk(dir_path):
        
        for file_name in file_names:
            
            name = _get_command_set_name(file_name)
            file_path = os.path.join(dir_path, file_name)
            
            try:
                command_sets[name] = _parse_command_set(file_path)
                
            except ValueError as e:
                print(str(e))
                continue
            
    return command_sets
            
            
def _get_command_set_name(file_name):
    if file_name.endswith(_TEXT_FILE_NAME_EXTENSION):
        return file_name[:-len(_TEXT_FILE_NAME_EXTENSION)]
    else:
        return file_name
    
    
def _parse_command_set(file_path):
    
    try:
        file_ = open(file_path, 'rU')
    except:
        f = 'Could not open classification command set file "{:s}".'
        raise ValueError(f.format(file_path))
    
    try:
        text = file_.read()
    except ValueError:
        f = 'Could not read classification command set file "{:s}".'
        raise ValueError(f.format(file_path))
    finally:
        file_.close()
        
    try:
        return command_set_utils.parse_command_set(text)
    except ValueError as e:
        f = 'Could not parse classification command set file "{:s}": {:s}'
        raise ValueError(f.format(file_path, str(e)))
    
    
preferences = _load_preferences()
