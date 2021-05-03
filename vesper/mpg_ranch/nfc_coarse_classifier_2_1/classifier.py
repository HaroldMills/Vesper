"""
Module containing MPG Ranch NFC coarse classifier, version 2.1.

An NFC coarse classifier classifies an unclassified clip as a `'Call'`
if it appears to be a nocturnal flight call, or as a `'Noise'` otherwise.
It does not classify a clip that has already been classified, whether
manually or automatically.

Version 2.1 of this classifier differs from version 2.0 only in that
it uses the `tensorflow.keras` module instead of the `keras` module.
The neural network model of version 2.1 is identical to the model of
version 2.0 (i.e. it has the same architecture and the same weights
and biases), and in principal should produce the same output for the
same input.
"""


import resampy

from vesper.command.annotator import Annotator
from vesper.mpg_ranch.nfc_coarse_classifier_2_1.feature_computer import \
    FeatureComputer
from vesper.singleton.clip_manager import clip_manager
from vesper.util.settings import Settings
import vesper.django.app.model_utils as model_utils
import vesper.mpg_ranch.nfc_coarse_classifier_2_1.classifier_utils as \
    classifier_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.yaml_utils as yaml_utils


class Classifier(Annotator):
    
    
    extension_name = 'MPG Ranch NFC Coarse Classifier 2.1'

    
    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        open_mp_utils.work_around_multiple_copies_issue()
        
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
    
    
    def _load_model(self):
        
        # We put this here rather than at the top of this module since
        # Keras can be rather slow to import (we have seen load times of
        # about ten seconds), so we want to import it only when we know
        # we are about to use it.
        from tensorflow import keras
        
        path = classifier_utils.get_model_file_path(self._clip_type)
        return keras.models.load_model(str(path))
    
    
    def _load_settings(self):
        path = classifier_utils.get_settings_file_path(self._clip_type)
        text = path.read_text()
        d = yaml_utils.load(text)
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
        
        samples = clip_manager.get_samples(clip)
        sample_rate = clip.sample_rate
        
        classifier_sample_rate = self._settings.waveform_sample_rate
        
        if sample_rate != classifier_sample_rate:
            # samples are not at classifier sample rate
            
            samples = resampy.resample(
                samples, sample_rate, classifier_sample_rate)
            
        return samples
