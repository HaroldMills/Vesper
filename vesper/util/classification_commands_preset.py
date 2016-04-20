"""Module containing `ClassificationCommandsPreset` class."""


import yaml

from vesper.util.preset import Preset
import vesper.util.extension_manager as extension_manager


class ClassificationCommandsPreset(Preset):
    
    """Preset for a set of clip classification commands."""
    
    
    type_name = 'Classification Commands'
    
    
    @staticmethod
    def parse_command_name(name):
        return _parse_command_name(name)


    def __init__(self, name, data):
        super().__init__(name)
        self._commands = _parse_preset(data)


    @property
    def commands(self):
        return dict(self._commands)
        
        
_SEPARATOR = '+'
"""Command component separator."""

_MODIFIERS = frozenset(['Alt'])
"""Set of recognized command modifiers, excluding shift."""

_DEFAULT_ACTION_NAME = 'Classify'
"""Default clip action name."""

_SCOPES = frozenset(['Selected', 'Page', 'All'])
"""Set of recognized command scopes."""

_DEFAULT_SCOPE = 'Selected'
"""Default command scope."""


def _parse_preset(text):
    
    try:
        commands = yaml.load(text)
    except Exception as e:
        raise ValueError(
            'Preset YAML parse failed. Error message was:\n{}'.format(str(e)))
    
    if not isinstance(commands, dict):
        raise ValueError('Preset text is not a YAML mapping.')
    
    return dict(_parse_command(*item) for item in commands.items())


def _parse_command(name, action):
    
    _parse_command_name(name)
    
    try:
        action = _parse_command_action(action)
    except ValueError as e:
        raise ValueError('Bad command "{}": {}'.format(name, str(e)))
    
    return (name, action)


def _parse_command_name(name):
    
    try:
        return _parse_command_name_aux(name)
    
    except Exception as e:
        
        # Quote name if and only if it is a string.
        if isinstance(name, str):
            n = '"{}"'.format(name)
        else:
            n = str(name)
            
        raise ValueError('Bad command name {}: {}'.format(n, str(e)))


def _parse_command_name_aux(name):
    
    if not isinstance(name, str):
        raise ValueError(
            'Name is of type {} rather than string.'.format(
                name.__class__.__name__))
        
    modifiers, char = _split_command_name(name)
    
    _check_modifiers(modifiers)
    _check_command_char(char)
    
    return (modifiers, char)
        
        
def _split_command_name(name):
    
    if len(name) < 2:
        return ([], name)
    
    elif name.endswith(_SEPARATOR * 2):
        modifiers = name[:-2].split(_SEPARATOR)
        return (modifiers, _SEPARATOR)
    
    else:
        parts = name.split(_SEPARATOR)
        return (parts[:-1], parts[-1])
    

def _check_modifiers(modifiers):
    for m in modifiers:
        if m not in _MODIFIERS:
            raise ValueError('Unrecognized modifier "{}".'.format(m))
    
    
def _check_command_char(char):
    if len(char) != 1:
        raise ValueError('A command must have exactly one character.')


def _parse_command_action(spec):
    
    if isinstance(spec, str):
        spec = {'class': spec, }
        
    elif not isinstance(spec, dict):
        raise ValueError(
            'Action must be either clip class name or mapping.')
        
    clip_action = _parse_clip_action(spec)
    scope = _parse_command_scope(spec)
    
    return (clip_action, scope)


def _parse_clip_action(spec):
    
    action_name = spec.get('action', _DEFAULT_ACTION_NAME)
    
    if action_name == 'None':
        return _EmptyAction()
    
    elif action_name == 'Classify':
        return _create_classify_action(spec)
    
    else:
        raise ValueError(
            ('Unrecognized action "{}". Action must be either '
             '"Classify" or "None".').format(action_name))


def _parse_command_scope(spec):
    
    scope = spec.get('scope', _DEFAULT_SCOPE)
    
    if scope not in _SCOPES:
        raise ValueError(
            ('Unrecognized scope "{}". Scope must be "Selected", '
             '"Page", or "All".').format(scope))
            
    return scope
        

def _create_classify_action(spec):
    
    if 'class' in spec and 'classifier' in spec:
        raise ValueError(
            'Action cannot include both "class" and "classifier" keys.')

    elif 'class' in spec:
        classifier = _FixedClassifier(spec['class'])
        return _ClassifyAction(classifier)
    
    elif 'classifier' in spec:
        
        name = spec['classifier']
        classes = extension_manager.get_extensions('Clip Classifier')
        
        try:
            cls = classes[name]
        except KeyError:
            raise ValueError(
                'Unrecognized clip classifier name "{}".'.format(name))
            
        classifier = cls()
        
        return _ClassifyAction(classifier)
    
    else:
        raise ValueError(
            'Action must include either "class" key or "classifier" key.')
    
    
class _EmptyAction(object):
    def execute(self, clip):
        pass
    
    
class _FixedClassifier(object):
    
    def __init__(self, clip_class_name):
        self._clip_class_name = clip_class_name
        
    def classify(self, clip):
        return self._clip_class_name
    
    
class _ClassifyAction(object):
    
    def __init__(self, classifier):
        self._classifier = classifier
        
    def execute(self, clip):
        clip_class_name = self._classifier.classify(clip)
        if clip_class_name is not None:
            if clip_class_name == 'Unclassified':
                clip_class_name = None
            clip.clip_class_name = clip_class_name
