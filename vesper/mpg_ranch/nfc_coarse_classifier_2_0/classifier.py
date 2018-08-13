"""
Module containing MPG Ranch NFC coarse classifier, version 2.0.

An NFC coarse classifier classifies an unclassified clip as a `'Call'`
if it appears to be a nocturnal flight call, or as a `'Noise'` otherwise.
It does not classify a clip that has already been classified, whether
manually or automatically.
"""


import resampy
import yaml

from vesper.command.annotator import Annotator
from vesper.mpg_ranch.nfc_coarse_classifier_2_0.feature_computer import \
    FeatureComputer
from vesper.singletons import clip_manager
from vesper.util.settings import Settings
import vesper.django.app.model_utils as model_utils
import vesper.mpg_ranch.nfc_coarse_classifier_2_0.classifier_utils as \
    classifier_utils


class Classifier(Annotator):
    
    
    extension_name = 'MPG Ranch NFC Coarse Classifier 2.0'

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self._classifiers = dict(
            (t, _Classifier(t)) for t in ('Thrush', 'Tseep'))
        
        
    def annotate(self, clip):
        
        annotated = False
        
        classification = self._get_annotation_value(clip)
        
        if classification is None:
            # clip is unclassified
            
            clip_type = model_utils.get_clip_type(clip)
            classifier = self._classifiers.get(clip_type)
        
            if classifier is not None:
                # clip is of a type for which we have a classifier
                
                classification = classifier.classify(clip)
                
                if classification is not None:
                    self._annotate(clip, classification)
                    annotated = True
                    
        return annotated
    

class _Classifier:
    
    
    def __init__(self, clip_type):
        
        self._clip_type = clip_type
        
        self._model = self._load_model()
        self._settings = self._load_settings()
        self._feature_computer = FeatureComputer(self._settings)
        self._clip_manager = clip_manager.instance
    
    
    def _load_model(self):
        
        # We put this here rather than at the top of this module since
        # Keras can be rather slow to import (we have seen load times of
        # about ten seconds), so we want to import it only when we know
        # we are about to use it.
        import keras
        
        path = classifier_utils.get_model_file_path(self._clip_type)
        return keras.models.load_model(path)
    
    
    def _load_settings(self):
        path = classifier_utils.get_settings_file_path(self._clip_type)
        text = path.read_text()
        d = yaml.load(text)
        return Settings.create_from_dict(d)
        
        
    def classify(self, clip):
        
        waveform = self._get_waveform(clip)
        
        if len(waveform) < self._feature_computer.min_waveform_length:
            # clip is too short to classify
            
            return 'Noise'
        
        else:
            # clip is not too short to classify
        
            # Add extra initial dimension to waveform array for feature
            # computer.
            waveforms = waveform.reshape((1,) + waveform.shape)
            
            features = self._feature_computer.compute_features(waveforms)
            
            value = self._model.predict(features, batch_size=1)[0]
            
            if value >= self._settings.classification_threshold:
                return 'Call'
            else:
                return 'Noise'
        
        
    def _get_waveform(self, clip):
        
        samples = self._clip_manager.get_samples(clip)
        sample_rate = clip.sample_rate
        
        classifier_sample_rate = self._settings.waveform_sample_rate
        
        if sample_rate != classifier_sample_rate:
            # samples are not at classifier sample rate
            
            samples = resampy.resample(
                samples, sample_rate, classifier_sample_rate)
            
        return samples
