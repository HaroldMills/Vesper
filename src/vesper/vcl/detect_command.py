"""Module containing class `DetectCommand`."""


from vesper.vcl.command import Command, CommandSyntaxError
import vesper.util.extension_manager as extension_manager


class DetectCommand(Command):
    
    """vcl command that runs a detector and archives the resulting clips."""
    
    
    name = 'detect'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        return _get_help(positional_args, keyword_args)

    
    def __init__(self, positional_args, keyword_args):
        
        super(DetectCommand, self).__init__()
        
        # TODO: Move this check to superclass. Note that subcommand
        # may have positional arguments, so it's not correct to test
        # for exactly one argument.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        detector_class = _get_detector_class(positional_args[0])
        self._detector = detector_class(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._detector.detect()
        
        
def _get_help(positional_args, keyword_args):

    n = len(positional_args)
    if n == 0:
        return _get_general_help()
    else:
        return _get_specific_help(positional_args, keyword_args)
    

'''
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual detectors from the detectors.
        return ('detect "Old Bird" --detectors <detector names> '
                '--input-mode File --input-paths <input files/dirs> '
                '[--archive <archive dir>]')
'''

    
_HELP = '''
detect <detector> [<positional arguments>] [<keyword arguments>]

Runs a detector on one or more inputs.

The detector to use and its configuration are specified by the
<detector> argument and the remaining arguments.

Type "vcl help detect <detector>" for help regarding a particular
detector.

Available detectors:
'''.strip()


def _get_general_help():
    
    classes = extension_manager.get_extensions('VCL Detector')
    names = classes.keys()
    names.sort()
    names = '\n'.join(('    ' + n) for n in names)
    
    return _HELP + '\n' + names
    
    
def _get_specific_help(positional_args, keyword_args):
    
    try:
        klass = _get_detector_class(positional_args[0])
    except CommandSyntaxError as e:
        return str(e)
    else:
        help_ = klass.get_help(positional_args[1:], keyword_args)
        return DetectCommand.name + ' ' + help_


def _get_detector_class(name):

    classes = extension_manager.get_extensions('VCL Detector')
    
    try:
        return classes[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized detector "{:s}".'.format(name))
