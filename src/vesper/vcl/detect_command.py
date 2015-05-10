"""Module containing class `DetectCommand`."""


from old_bird.detector import Detector as OldBirdDetector
from vesper.vcl.command import Command, CommandSyntaxError


_DETECTOR_CLASSES = {
    'Old Bird': OldBirdDetector
}


class DetectCommand(Command):
    
    """vcl command that runs a detector and archives the resulting clips."""
    
    
    name = 'detect'
    
    
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual detectors from the detectors.
        return ('detect "Old Bird" --detectors <detector names> '
                '--input-mode File --input-paths <input files/dirs> '
                '[--archive <archive dir>]')

    
    def __init__(self, positional_args, keyword_args):
        
        super(DetectCommand, self).__init__()
        
        # TODO: Move this check to superclass. Note that subcommand
        # may have positional arguments, so it's not correct to test
        # for exactly one argument.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        klass = _get_detector_class(positional_args[0])
        self._detector = klass(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._detector.detect()
        
        
def _get_detector_class(name):

    try:
        return _DETECTOR_CLASSES[name]
    except KeyError:
        raise CommandSyntaxError('Unrecognized detector "{:s}".'.format(name))
