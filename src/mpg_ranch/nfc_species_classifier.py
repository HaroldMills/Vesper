"""
Module containing class `NfcSpeciesClassifier`.

An `NfcSpeciesClassifier` assigns a `"Call"` clip to a particular species
(or species complex) if the classifier is sufficiently confident that the
call was produced by that species. The classifier does not change the
classification otherwise. The classifier does not change the classification
of any clip whose classification is not `"Call"`, including clips that are
already classified to subclasses of the `"Call"` class.
"""


import pickle
import os.path

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Assigns clips of the "Call" clip class to more specific clip classes.

This classifier assigns a "Call" clip to a particular species (or species
complex) clip class if it is sufficiently confident that the call belongs
to that class. The classifier does not change the classification otherwise.
The classifier does not change the classification of any clip whose
classification is not `"Call"`, including clips that are already classified
to subclasses of the `"Call"` class.

See the keyword arguments documentation for how to specify the archive
in which clips are to be classified, and the subset of clips of that
archive to be classified.
'''.strip()


class NfcSpeciesClassifier(object):
    
    
    name = 'MPG Ranch NFC Species Classifier'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(NfcSpeciesClassifier.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(NfcSpeciesClassifier, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def classify(self):
        return self._clip_visitor.visit_clips()
        
        
_DETECTOR_NAMES = ['Tseep']


class _ClipVisitor(ClipVisitor):
    
    
    def __init__(self, positional_args, keyword_args):
        super(_ClipVisitor, self).__init__(positional_args, keyword_args)
        self._classifier = NfcSpeciesClipClassifier()
        
        
    def visit(self, clip):
        if clip.clip_class_name == 'Call':
            classifier = self._classifiers.get(clip.detector_name)
            if classifier is not None:
                clip_class_name = classifier.classify_clip(clip)
                if clip_class_name is not None:
                    clip.clip_class_name = clip_class_name
                

class NfcSpeciesClipClassifier(object):
    
    
    name = 'MPG Ranch NFC Species Clip Classifier'
    
    
    def __init__(self):
        self._classifiers = {}
        for name in _DETECTOR_NAMES:
            classifier = _create_classifier(name)
            if classifier is not None:
                self._classifiers[name] = classifier
        
        
    def classify(self, clip):
        if clip.clip_class_name == 'Call':
            classifier = self._classifiers.get(clip.detector_name)
            if classifier is not None:
                clip_class_name = classifier.classify_clip(clip)
                if clip_class_name is not None:
                    clip.clip_class_name = clip_class_name


def _create_classifier(name):

    package_dir_path = os.path.dirname(__file__)
    file_name = '{} Species Classifier.pkl'.format(name)
    file_path = os.path.join(package_dir_path, file_name)

    try:
        with open(file_path, 'rb') as file_:
            return pickle.load(file_)
    except Exception as e:
        raise ValueError(
            ('Could not create classifier "{}". Error message '
             'was: {}').format(name, str(e)))
