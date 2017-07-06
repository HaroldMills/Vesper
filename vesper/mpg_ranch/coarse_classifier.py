"""
Module containing class `CoarseClassifier`.

A `CoarseClassifier` classifies an unclassified clip as a `'Call'` if
it appears to be a nocturnal flight call. It does not classify an
unclassified clip that does not appear to be a nocturnal flight call,
or alter the classification of a clip that has already been classified.
"""


from vesper.command.annotator import Annotator
import vesper.django.app.model_utils as model_utils
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier


class CoarseClassifier(Annotator):
    
    
    extension_name = 'MPG Ranch Coarse Classifier 1.0'
    
    
    def begin_annotations(self):
        create = nfc_coarse_classifier.create_classifier
        self._classifiers = dict(
            (name, create(name)) for name in ('Tseep', 'Thrush'))
    
    
    def annotate(self, clip):
        
        annotated = False
        
        classification = self._get_annotation_value(clip)
        
        if classification is None:
            # clip is unclassified
            
            clip_type = model_utils.get_clip_type(clip)
        
            if clip_type is not None:
                # clip was detected by Old Bird Tseep or Thrush
                
                classifier = self._classifiers[clip_type]
                classification = classifier.classify_clip(clip)
                
                if classification is not None:
                    self._annotate(clip, classification)
                    annotated = True
                    
        return annotated
