"""Module containing `ClassificationCommandsPreset` class."""


import six
import yaml

from vesper.util.preset import Preset
import vesper.util.extension_manager as extension_manager


class ClassificationCommandsPreset(Preset):
    
    """Preset for a set of clip classification commands."""
    
    type_name = 'Classification Commands'
    
    def __init__(self, name, data):
        super(ClassificationCommandsPreset, self).__init__(name)
        self._commands = _parse_preset(data)

    @property
    def commands(self):
        return dict(self._commands)
        
        
_MODIFIERS = frozenset(['Alt'])
"""set of recognized command modifiers, excluding shift."""

_DEFAULT_ACTION_NAME = 'Classify'
"""Default clip action name."""

_SCOPES = frozenset(['Selected', 'Page', 'All'])
"""set of recognized command scopes."""

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
    
    return dict(_parse_command(*item) for item in commands.iteritems())


def _parse_command(name, action):
    
    try:
        _check_command_name(name)
    except ValueError as e:
        raise ValueError('Bad command name "{}": {}'.format(name, str(e)))
    
    try:
        action = _parse_command_action(action)
    except ValueError as e:
        raise ValueError('Bad command "{}": {}'.format(name, str(e)))
    
    else:
        return (name, action)


def _check_command_name(name):
    
    if not isinstance(name, six.string_types):
        raise ValueError(
            'Name is of type {} rather than string.'.format(
                name.__class__.__name__))
        
    parts = name.split('-')
    
    if len(parts) == 1:
        _check_command_char(parts[0])
        
    else:
        _check_modifiers(parts[:-1])
        _check_command_char(parts[-1])
        
        
def _check_command_char(char):
    if len(char) != 1:
        raise ValueError('A command must have exactly one character.')


def _check_modifiers(modifiers):
    for m in modifiers:
        if m not in _MODIFIERS:
            raise ValueError('Unrecognized modifier "{}".'.format(m))
    
    
def _parse_command_action(spec):
    
    if isinstance(spec, six.string_types):
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
    
    if spec.has_key('class') and spec.has_key('classifier'):
        raise ValueError(
            'Action cannot include both "class" and "classifier" keys.')

    elif spec.has_key('class'):
        classifier = _FixedClassifier(spec['class'])
        return _ClassifyAction(classifier)
    
    elif spec.has_key('classifier'):
        
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
    