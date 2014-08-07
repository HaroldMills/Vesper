"""Module containing NFC Viewer preferences."""


from __future__ import print_function

import json
import os.path
import sys
        
            
_NFC_DIR_NAME = 'NFC'
_PREFERENCES_FILE_NAME = 'Preferences.json'


def _load_preferences():
    
    home_dir_path = os.path.expanduser('~')
    file_path = \
        os.path.join(home_dir_path, _NFC_DIR_NAME, _PREFERENCES_FILE_NAME)
    
    try:
        file_ = open(file_path, 'rU')
    except:
        f = 'Could not open preferences file "{:s}".'
        _handle_error(f.format(file_path))
    
    try:
        preferences = json.load(file_)
    except ValueError:
        file_.close()
        f = 'Could not parse preferences file "{:s}".'
        _handle_error(f.format(file_path))

    file_.close()
        
    try:
        preferences['classification.commandSets'] = \
            _parse_command_sets(preferences['classification.commandSets'])
    except ValueError as e:
        f = 'Could not parse command sets in preferences file "{:s}". {:s}'
        _handle_error(f.format(file_path, str(e)))

    return preferences


def _handle_error(message):
    print(message, file=sys.stderr)
    sys.exit(1)
    
    
def _parse_command_sets(commandSets):
    return dict(_parse_command_set(*i) for i in commandSets.iteritems())


def _parse_command_set(name, lines):
    lines = [line.strip() for line in lines]
    pairs = [_parseCommand(line, i + 1, name)
             for i, line in enumerate(lines) if line != '']
    return (name, dict(pairs))


_SCOPES = frozenset(['Selected', 'Page', 'All'])


def _parseCommand(line, lineNum, commandSetName):
    
    items = line.split()
    n = len(items)
    
    if n < 2 or n > 3:
        raise ValueError(
            ('Bad command specification "{:s}" for command set "{:s}": '
             'specification must have either two or three components '
             'separated by spaces.').format(line, commandSetName))
    
    name = items[0]
    command = items[1]
    scope = items[2] if n == 3 else 'Selected'
    
    if scope not in _SCOPES:
        f = ('Bad command specification "{:s}" for command set "{:s}": '
             'third component must be "Page" or "All".')
        raise ValueError(f.format(line, commandSetName))
        
    return (name, (command, scope))


preferences = _load_preferences()
