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
