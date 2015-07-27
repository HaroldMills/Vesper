"""Module containing class `ClassifyCommand`."""


from __future__ import print_function

from vesper.vcl.command import Command, CommandSyntaxError
import vesper.util.extension_manager as extension_manager


class ClassifyCommand(Command):
    
    """vcl command that classifies clips of an archive."""
    
    
    name = 'classify'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        return _get_help(positional_args, keyword_args)

    
    def __init__(self, positional_args, keyword_args):
        
        super(ClassifyCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        classifier_class = _get_classifier_class(positional_args[0])
        self._classifier = classifier_class(positional_args[1:], keyword_args)
        
        
    def execute(self):
        self._classifier.classify()

    
def _get_help(positional_args, keyword_args):

    n = len(positional_args)
    if n == 0:
        return _get_general_help()
    else:
        return _get_specific_help(positional_args, keyword_args)
    

_HELP = '''
classify <classifier> [<positional arguments>] [<keyword arguments>]

Classifies clips of an archive.

The classifier to use and which clips to classify are specified by the
<classifier> argument and the remaining arguments.

Type "vcl help classify <classifier>" for help regarding a particular
classifier.

Available classifiers:
'''.strip()


def _get_general_help():
    
    classes = extension_manager.get_extensions('VCL Classifier')
    names = classes.keys()
    names.sort()
    names = '\n'.join(('    ' + n) for n in names)
    
    return _HELP + '\n' + names
    
    
def _get_specific_help(positional_args, keyword_args):
    
    classes = extension_manager.get_extensions('VCL Classifier')
    name = positional_args[0]
    klass = classes.get(name)
    
    if klass is None:
        return 'Unrecognized classifier "{:s}".'.format(name)
    
    else:
        help_ = klass.get_help(positional_args[1:], keyword_args)
        return ClassifyCommand.name + ' ' + help_


def _get_classifier_class(name):
    
    classifier_classes = extension_manager.get_extensions('VCL Classifier')
    
    try:
        return classifier_classes[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized classifier "{:s}".'.format(name))
