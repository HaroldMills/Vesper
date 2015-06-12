"""Module containing class `ClassifyCommand`."""


from __future__ import print_function

from mpg_ranch.outside_clip_classifier \
    import OutsideClipClassifier as MpgRanchOutsideClipClassifier
from vesper.vcl.clip_visitor import ClipVisitor
from vesper.vcl.command import Command, CommandSyntaxError
import vesper.vcl.vcl_utils as vcl_utils


# TODO: Make classification commands work more like export commands,
# i.e. eliminate the "--classifier" keyword argument.


class ClassifyCommand(Command):
    
    """vcl command that classifies clips of an archive."""
    
    
    name = 'classify'
    
    
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual classifiers from the classifiers.
        return (
            'classify clips '
            '--classifier "MPG Ranch Outside Clip Classifier" '
            '[--station <station name>] [--stations <station names>] '
            '[--detector <detector name>] [--detectors <detector names>] '
            '[--clip-class <clip class name>] '
            '[--clip-classes <clip class names>] '
            '[--date <YYYY-MM-DD>] '
            '[--start-date <YYYY-MM-DD] [--end-date <YYYY-MM-DD>] '
            '[--archive <archive dir>]')

    
    def __init__(self, positional_args, keyword_args):
        
        super(ClassifyCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        klass = _get_classifier_class(positional_args[0])
        self._classifier = klass(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._classifier.visit_clips()
        
        
def _get_classifier_class(name):

    try:
        return _CLASSIFIER_CLASSES[name]
    except KeyError:
        raise ValueError(
            'Unrecognized classification object type "{:s}".'.format(name))


class ClipClassifier(ClipVisitor):
    
    
    def __init__(self, positional_args, keyword_args):
        super(ClipClassifier, self).__init__(positional_args, keyword_args)
        self._classifier = _get_clip_classifier(positional_args, keyword_args)
                
    
    def visit_clip(self, clip):
        self._classifier.classify(clip)


_CLIP_CLASSIFIER_CLASSES = {
    'MPG Ranch Outside Clip Classifier': MpgRanchOutsideClipClassifier
}


def _get_clip_classifier(positional_args, keyword_args):

    (name,) = vcl_utils.get_required_keyword_arg('classifier', keyword_args)
    
    try:
        klass = _CLIP_CLASSIFIER_CLASSES[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized clip classifier "{:s}".'.format(name))

    return klass(positional_args, keyword_args)


_CLASSIFIER_CLASSES = {
    'clips': ClipClassifier
}
