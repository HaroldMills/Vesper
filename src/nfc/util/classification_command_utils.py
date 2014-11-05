"""Utility functions pertaining to classification command sets."""


import operator

from PyQt4.QtCore import Qt


_ALPHABETIC_CHARS = 'abcdefghijklmnopqrstuvwxyz'
"""string of lower-case alphabetic characters."""

_CHARS_DICT = dict((eval('Qt.Key_' + c.upper()), c) for c in _ALPHABETIC_CHARS)
"""mapping from integer Qt key codes to lower-case characters."""

_CHARS = frozenset(_ALPHABETIC_CHARS + _ALPHABETIC_CHARS.upper())
"""set of recognized command characters."""

_MODIFIER_PAIRS = [('Alt', Qt.AltModifier)]
"""
list of recognized (modifier name, QT keyboard modifier flag) pairs,
excluding shift.

Note that we do *not* allow classification commands that use the control
modifier (i.e. the control key on Linux and Windows and the command key
on Mac OS X) since they could collide with menu item keyboard accelerators.
"""

_MODIFIER_NAMES = frozenset([p[0] for p in _MODIFIER_PAIRS])
"""set of recognized command modifier names, excluding shift."""

_ALL_MODIFIERS = reduce(
    operator.or_, [m for _, m in _MODIFIER_PAIRS], Qt.ShiftModifier)
"""disjunction of recognized command modifiers, including shift."""

_SCOPES = frozenset(['Selected', 'Page', 'All'])
"""set of recognized command scopes."""


def parse_command_set(text):
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line != '']
    pairs = [_parse_command_spec(line, i + 1) for i, line in enumerate(lines)]
    return dict(pairs)


def _parse_command_spec(line, lineNum):
    
    items = line.split()
    n = len(items)
    
    if n < 2 or n > 3:
        raise ValueError(
            ('Bad command specification "{:s}": specification '
             'must have either two or three components separated '
             'by spaces.').format(line))
    
    command = items[0]
    clip_class_name = items[1]
    scope = items[2] if n == 3 else 'Selected'
    
    _check_command(command)
    _check_scope(scope, line)
    
    return (command, (clip_class_name, scope))


def _check_command(command):
    
    parts = command.split('-')
    
    if len(parts) == 1:
        _check_command_char(parts[0], command)
        
    else:
        _check_modifiers(parts[:-1], command)
        _check_command_char(parts[-1], command)
        
        
def _check_command_char(char, command):
    
    if len(char) != 1:
        f = 'Bad command "{:s}": a command must have exactly one character.'
        raise ValueError(f.format(command))
    
    if char not in _CHARS:
        f = ('Bad command "{:s}": only alphabetic command characters '
             'are allowed.')
        raise ValueError(f.format(char, command))


def _check_modifiers(modifiers, command):
    for m in modifiers:
        if m not in _MODIFIER_NAMES:
            f = 'Unrecognized modifier "{:s}" in command "{:s}".'
            raise ValueError(f.format(m, command))
    
    
def _check_scope(scope, spec):
    if scope not in _SCOPES:
        f = ('Bad command specification "{:s}": third component '
             'must be "Selected", "Page", or "All".')
        raise ValueError(f.format(spec))
        

def get_command_from_key_event(key_event):
    
    char = _CHARS_DICT.get(key_event.key())
    
    if char is None:
        return None
    
    else:
        
        modifiers = key_event.modifiers()
        
        if modifiers | _ALL_MODIFIERS != _ALL_MODIFIERS:
            # unrecognized modifier present
            return None
            
        mods = ''.join(s + '-' for s, m in _MODIFIER_PAIRS if modifiers & m)

        if modifiers & Qt.ShiftModifier:
            char = char.upper()
            
        return mods + char


def is_key(key_event, key, modifiers=Qt.NoModifier):
     
    if key_event.key() != key:
        return False
     
    else:
        return key_event.modifiers() == modifiers
