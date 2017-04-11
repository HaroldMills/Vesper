"""
Module containing class `CoarseClassifier`.

A `CoarseClassifier` classifies an unclassified clip as a `'Call'` if
it appears to be a nocturnal flight call. It does not classify an
unclassified clip that does not appear to be a nocturnal flight call,
or alter the classification of a clip that has already been classified.
"""


import logging

from vesper.command.annotator import Annotator
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier


_logger = logging.getLogger()


class CoarseClassifier(Annotator):
    
    
    extension_name = 'MPG Ranch Coarse 1.0'
    
    
    def begin_annotations(self):
        create = nfc_coarse_classifier.create_classifier
        self._classifiers = dict(
            (name, create(name)) for name in ('Tseep', 'Thrush'))
    
    
    def annotate(self, clip):
        
        classification = self._get_annotation_value(clip)
        
        if classification is None:
            # clip is unclassified
            
            clip_type = _get_clip_type(clip)
        
            if clip_type is not None:
                # clip was detected by Old Bird Tseep or Thrush
                
                classifier = self._classifiers[clip_type]
                classification = classifier.classify_clip(clip)
                
                if classification is not None:
                    self._annotate(clip, classification)
        
            
def _get_clip_type(clip):
    
    processor = clip.creating_processor
    
    if processor is None:
        return None
    
    elif processor.name == 'Old Bird Tseep':
        return 'Tseep'
        
    elif processor.name == 'Old Bird Thrush':
        return 'Thrush'
    
    else:
        return None
