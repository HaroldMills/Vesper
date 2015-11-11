"""
Module containing class `CallClassifier`.

A `CallClassifier` assigns an `"Unclassified"` clip to the `"Call"` clip
class if the clip appears to contain a nocturnal flight call, and leaves
it unclassified otherwise.
"""


from __future__ import print_function

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.util.call_noise_classifier as coarse_classifier
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Assigns unclassified clips that appear to contain nocturnal flight calls to
the "Call" clip class.

Only unclassified clips are considered. An unclassified clip that appears
to contain a nocturnal flight call is assigned to the "Call" clip class.
Otherwise the clip is left unclassified.

See the keyword arguments documentation for how to specify the archive
in which clips are to be classified, and the subset of clips of that
archive to be classified.
'''.strip()


_ARG_DESCRIPTORS = \
    vcl_utils.ARCHIVE_ARG_DESCRIPTORS + \
    vcl_utils.CLIP_QUERY_ARG_DESCRIPTORS
    
    
class CoarseClassifier(object):
    
    
    name = 'Coarse Classifier'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(CoarseClassifier.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(CoarseClassifier, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def classify(self):
        return self._clip_visitor.visit_clips()
        
        
_DETECTOR_NAMES = ['Tseep']


class _ClipVisitor(ClipVisitor):
    
    
    def __init__(self, positional_args, keyword_args):
        super(_ClipVisitor, self).__init__(positional_args, keyword_args)
        self._classifiers = dict(
            (name, _create_classifier(name)) for name in _DETECTOR_NAMES)
        
        
    def visit(self, clip):
        
        if clip.clip_class_name == None:
            # clip is unclassified
            
            if self._is_call(clip):
                clip.clip_class_name = 'Call'


    def _is_call(self, clip):
        
        for detector_name, classifier in self._classifiers.iteritems():
            if clip.detector_name == detector_name and \
                    classifier.classify_clip(clip) == 1:
                return True
            
        # If we get here, none of the classifiers classified the clip
        # as a call.
        return False
                

def _create_classifier(detector_name):
    return coarse_classifier.create_classifier(detector_name)    

