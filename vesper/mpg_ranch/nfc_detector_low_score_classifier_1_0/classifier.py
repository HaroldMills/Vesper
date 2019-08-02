"""
Module containing low score classifier for MPG Ranch NFC detectors.

An instance of the `Classifier` class of this module assigns the `LowScore`
classification to a clip if the clip has no `Classification` annotation and
has a `DetectorScore` annotation whose value is less than a threshold.

This classifier is intended for use on clips created by the the
MPG Ranch Thrush Detector 1.0 and the MPG Ranch Tseep Detector 1.0.
"""


import logging

from vesper.command.annotator import Annotator
from vesper.django.app.models import AnnotationInfo, StringAnnotation


_logger = logging.getLogger()


_SCORE_THRESHOLDS = {
    
    # For 50 percent precision on validation recordings.
    'MPG Ranch Thrush Detector 1.0 40': 70,
    'MPG Ranch Tseep Detector 1.0 20': 41,
    
    # For 75 percent precision on validation recordings.
    # 'MPG Ranch Thrush Detector 1.0 40': 91,
    # 'MPG Ranch Tseep Detector 1.0 20': 63,

}


class Classifier(Annotator):
    
    
    extension_name = 'MPG Ranch NFC Detector Low Score Classifier 1.0'
    
    
    def __init__(
            self, annotation_info, creating_user=None, creating_job=None,
            creating_processor=None):
        
        super().__init__(
            annotation_info, creating_user, creating_job, creating_processor)
        
        self._score_annotation_info = _get_annotation_info('Detector Score')
        
        self._score_thresholds = _SCORE_THRESHOLDS
        
        
    def annotate(self, clip):
        
        annotated = False
        
        classification = self._get_annotation_value(clip)
        
        if classification is None:
            # clip is unclassified
            
            score = self._get_score(clip)
            
            if score is not None:
                # clip has a detector score
                
                threshold = self._get_score_threshold(clip)
                
                if threshold is not None and score < threshold:
                    # detector score is below threshold
                    
                    self._annotate(clip, 'LowScore')
                    annotated = True
                
        return annotated


    def _get_score(self, clip):
        try:
            annotation = StringAnnotation.objects.get(
                clip=clip, info=self._score_annotation_info)
        except StringAnnotation.DoesNotExist:
            return None
        else:
            return float(annotation.value)
        
        
    def _get_score_threshold(self, clip):
        detector = clip.creating_processor
        if detector is None:
            return None
        else:
            return self._score_thresholds.get(detector.name)
        

def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(name=name)
    except AnnotationInfo.DoesNotExist:
        raise ValueError(
            'Unrecognized annotation "{}".'.format(name))
