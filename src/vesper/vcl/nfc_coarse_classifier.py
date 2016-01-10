"""
Module containing class `NfcCoarseClassifier`.

An `NfcCoarseClassifier` assigns an `"Unclassified"` clip to the `"Call"`
clip class if the clip appears to contain a nocturnal flight call, and
leaves it unclassified otherwise.
"""


from __future__ import print_function

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier
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


class NfcCoarseClassifier(object):
    
    
    name = 'NFC Coarse Classifier'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(NfcCoarseClassifier.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(NfcCoarseClassifier, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def classify(self):
        return self._clip_visitor.visit_clips()
        
        
_DETECTOR_NAMES = ['Thrush', 'Tseep']


class _ClipVisitor(ClipVisitor):
    
    
    def __init__(self, positional_args, keyword_args):
        super(_ClipVisitor, self).__init__(positional_args, keyword_args)
        self._classifiers = _create_classifiers()
        
        
    def visit(self, clip):
        if clip.clip_class_name is None:
            classifier = self._classifiers.get(clip.detector_name)
            if classifier is not None:
                clip_class_name = classifier.classify_clip(clip)
                if clip_class_name is not None:
                    clip.clip_class_name = clip_class_name
                

def _create_classifiers():
    create_classifier = nfc_coarse_classifier.create_classifier
    return dict((name, create_classifier(name)) for name in _DETECTOR_NAMES)
