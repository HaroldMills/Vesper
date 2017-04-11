"""
Module containing class `SpeciesClassifier`.

A `SpeciesClassifier` classifies some `'Call'` clips to species.
It does not classify any clips that are not already classified as
`'Call'`.

The classifier currently only attempts to classify tseep calls.
"""


import os.path
import pickle

from vesper.command.annotator import Annotator


class SpeciesClassifier(Annotator):
    
    
    extension_name = 'MPG Ranch Species 1.0'
    
    
    def begin_annotations(self):
        self._classifier = _create_classifier('Tseep')
    
    
    def annotate(self, clip):
        
        classification = self._get_annotation_value(clip)
        
        if classification == 'Call':
            # clip is classified as a call, but not to species
            
            clip_type = _get_clip_type(clip)
        
            if clip_type == 'Tseep':
                # clip was detected by Old Bird Tseep
                
                classification = self._classifier.classify_clip(clip)
                
                if classification is not None:
                    self._annotate(clip, classification)
        
            
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
