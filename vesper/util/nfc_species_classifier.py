"""Module containing class `NfcSpeciesClassifier`."""


import numpy as np

from vesper.singleton.clip_manager import clip_manager
from vesper.util.bunch import Bunch
from vesper.util.signal_utils import seconds_to_frames
import vesper.util.nfc_classification_utils as nfc_classification_utils
import vesper.util.nfc_detection_utils as nfc_detection_utils
import vesper.util.signal_utils as signal_utils


_CLASSIFICATION_SAMPLE_RATE = 22050


class NfcSpeciesClassifier(object):
    
    
    def __init__(self, config, segment_classifier):
        super(NfcSpeciesClassifier, self).__init__()
        self._config = config
        self._segment_classifier = segment_classifier
        
        
    @property
    def clip_class_names(self):
        return self._segment_classifier.clip_class_names

    
    def classify_clip(self, clip):
        
        # Our species classifiers are designed for clips with a particular
        # sample rate, so resample to that rate if needed.
        audio = clip_manager.get_audio(clip)
        audio = signal_utils.resample(audio, _CLASSIFICATION_SAMPLE_RATE)
        
        selection = find_call(audio, self._config)
        
        if selection is None:
            return None
        
        call = extract_call(audio, selection, self._config)
        
        if call is None:
            return None
        
        features, _, _ = nfc_classification_utils.get_segment_features(
            call, self._config)
        
        clip_class_name = self._segment_classifier.predict([features])[0]
        
        if clip_class_name == 'Unclassified':
            return None
        else:
            return clip_class_name


class SegmentClassifier(object):
    
    """
    Multi-class segment classifier that wraps a scikit-learn multi-class
    classifier.
    """
    
    
    def __init__(self, classifier, clip_class_names):
        super(SegmentClassifier, self).__init__()
        self._classifier = classifier
        self._clip_class_names = sorted(clip_class_names)
        
    
    @property
    def clip_class_names(self):
        return list(self._clip_class_names)
    
    
    def predict(self, features):
        return self._classifier.predict(features)
    
    
class CompositeSegmentClassifier(object):
    
    """
    Multi-class segment classifier built from a collection of scikit-learn
    binary classifiers.
    
    The composite classifier classifies a segment to a binary classifier's
    class if and only if that classifier is the only binary classifier that
    claims the segment. If none of the binary classifiers claims a segment,
    or if more than one of them claims a segment, the segment is classified
    as "Unclassified".
    """
    
    
    def __init__(self, classifiers):
        super(CompositeSegmentClassifier, self).__init__()
        self.classifiers = classifiers
        names = sorted(self.classifiers.keys())
        self._clip_class_names_tuple = tuple(['Unclassified',] + names)
        self._clip_class_names_array = np.array(self._clip_class_names_tuple)
        
    
    @property
    def clip_class_names(self):
        return self._clip_class_names_tuple
    
    
    def predict(self, features):
        
        num_predictions = len(features)
        
        classifiers = self.classifiers
        num_species = len(classifiers)
        
        clip_class_names = self._clip_class_names_array[1:]
        predictions = np.zeros((num_species, num_predictions), dtype='int32')
        for i, clip_class_name in enumerate(clip_class_names):
            classifier = classifiers[clip_class_name]
            predictions[i] = classifier.predict(features)
            
        # Transpose predictions so `predictions[i, j]` is prediction of
        # classifier `j` for clip `i`.
        predictions = predictions.transpose()
            
        # Get booleans indicating which clips were positive for exactly
        # one species.
        indicators = predictions.sum(axis=1) == 1
        
        # Get predictions as integers in the range [0, num_species].
        # A prediction of zero indicates no species.
        integer_codes = np.arange(num_species) + 1
        predictions = predictions * integer_codes
        predictions = predictions.sum(axis=1)
        predictions[~indicators] = 0
        
        # Get predictions as clip class names.
        predictions = self._clip_class_names_array[predictions]

        return predictions        


def find_call(audio, config):
    
    # TODO: Why does `detect_tseeps` return selections in seconds?
    # TODO: We're tied to tseeps here since we call `detect_tseeps`.
    # Perhaps we should call `detect_events` with an appropriate
    # detector configuration instead.
    selections = nfc_detection_utils.detect_tseeps(audio)
    selection = nfc_detection_utils.get_longest_selection(selections)
    
    if selection is None:
        return None
    
    else:
        start_time, end_time = selection
        sample_rate = float(audio.sample_rate)
        start_index = seconds_to_frames(start_time, sample_rate)
        end_index = seconds_to_frames(end_time, sample_rate)
        return (start_index, end_index)
    
    
def extract_call(audio, selection, config):
    
    samples = audio.samples
    sample_rate = audio.sample_rate

    start_index, end_index = selection
    center_index = (start_index + end_index - 1) // 2
    
    duration = config.call_segment_duration
    length = seconds_to_frames(duration, sample_rate)
    start_index = center_index - length // 2
    
    if start_index < 0:
        return None
    
    else:
        # start index is at least zero
        
        end_index = start_index + length
        
        if end_index > len(samples):
            return None
        
        else:
            return Bunch(
                samples=samples[start_index:end_index],
                sample_rate=sample_rate)
