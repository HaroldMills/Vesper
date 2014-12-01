"""Module containing `ClassificationCommandsPreset` class."""


from nfc.util.preset import Preset


class ClassificationCommandsPreset(Preset):
    
    """Preset for a set of clip classification commands."""
    
    
    type_name = 'Classification Commands'
    
    
    def __init__(self, name, data):
        super(ClassificationCommandsPreset, self).__init__(name)
        self._commands = _parse_preset(data)

    
    @property
    def commands(self):
        return dict(self._commands)
        
        
_ALPHABETIC_CHARS = 'abcdefghijklmnopqrstuvwxyz'
"""string of lower-case alphabetic characters."""

_CHARS = frozenset(_ALPHABETIC_CHARS + _ALPHABETIC_CHARS.upper())
"""set of recognized command characters."""

_MODIFIER_NAMES = frozenset(['Alt'])
"""set of recognized command modifier names, excluding shift."""

_SCOPES = frozenset(['Selected', 'Page', 'All'])
"""set of recognized command scopes."""


def _parse_preset(text):
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
