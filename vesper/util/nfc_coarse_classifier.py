"""Module containing class `NfcCoarseClassifier`."""


import pickle
import os.path
import random

import numpy as np

from vesper.singleton.clip_manager import clip_manager
from vesper.util.bunch import Bunch
import vesper.util.nfc_classification_utils as nfc_classification_utils
import vesper.util.signal_utils as signal_utils


# TODO: Think more about where data files should go, and how this interacts
# with the plugin facility.

# TODO: Support multiple classifier versions. Perhaps the code and data
# for a particular classifier version should go in its own Python package,
# and the package name should include the version number? I'm not sure
# this will really work, though, since different classifier versions
# might depend on different versions of other packages.


SEGMENT_SOURCE_CLIP = 'Clip'
SEGMENT_SOURCE_CLIP_CENTER = 'Clip Center'
SEGMENT_SOURCE_SELECTION = 'Selection'

_CLASSIFICATION_SAMPLE_RATE = 22050


def create_classifier(classifier_name):

    package_dir_path = os.path.dirname(__file__)
    file_name = '{} Coarse Classifier.pkl'.format(classifier_name)
    file_path = os.path.join(package_dir_path, file_name)

    # TODO: Handle load errors.
    with open(file_path, 'rb') as file_:
        return pickle.load(file_)


def extract_clip_segment(
        clip, segment_duration, segment_source, source_duration=None):
    
    source = _get_segment_source(clip, segment_source, source_duration)
    
    if source is None:
        return None
    
    else:
        
        source_start_index, source_length = source
        
        sample_rate = clip.sample_rate
        segment_length = signal_utils.seconds_to_frames(
            segment_duration, sample_rate)
        
        if source_length < segment_length:
            # source not long enough to extract segment from
            
            return None
            
        else:
            
            # Extract samples from source.
            if source_length == segment_length:
                offset = 0
            else:
                offset = random.randrange(source_length - segment_length)
            start_index = source_start_index + offset
            end_index = start_index + segment_length
            samples = clip_manager.get_samples(clip)
            samples = samples[start_index:end_index]
            
            return Bunch(
                samples=samples,
                sample_rate=clip.sample_rate,
                start_index=start_index)



def _get_segment_source(clip, segment_source, source_duration):
    
    source = segment_source
    clip_length = clip.length
        
    if source == SEGMENT_SOURCE_CLIP:
        return (0, clip_length)
        
    elif source == SEGMENT_SOURCE_CLIP_CENTER:
        
        sample_rate = clip.sample_rate
        source_length = signal_utils.seconds_to_frames(
            source_duration, sample_rate)
        
        if source_length >= clip_length:
            return (0, clip_length)
        
        else:
            source_start_index = int((clip_length - source_length) // 2)
            return (source_start_index, source_length)
            
    elif source == SEGMENT_SOURCE_SELECTION:
        return clip.selection
    
    else:
        raise ValueError(
            'Unrecognized clip segment source "{}".'.format(source))

    
class NfcCoarseClassifier(object):
    
    
    def __init__(self, config, segment_classifier):
        super(NfcCoarseClassifier, self).__init__()
        self._config = config
        self._segment_classifier = segment_classifier
        
        
    def classify_clip(self, clip):
        segment_classifications, _, _ = self.classify_clip_segments(clip)
        if np.any(segment_classifications == 1):
            return 'Call'
        else:
            return None
    
    
    def classify_clip_segments(self, clip):
        
        # Our classifiers are designed for clips with a particular sample
        # rate, so resample to that rate if needed.
        audio = clip_manager.get_audio(clip)
        audio = signal_utils.resample(audio, _CLASSIFICATION_SAMPLE_RATE)
        
        c = self._config
        
        u = signal_utils
        sample_rate = audio.sample_rate
        segment_length = u.seconds_to_frames(c.segment_duration, sample_rate)
        hop_size = u.seconds_to_frames(c.segment_hop_size, sample_rate)
        
        pairs = [self._classify_segment(s, c)
                 for s in _generate_segments(audio, segment_length, hop_size)]
                
        if len(pairs) == 0:
            classifications = np.array([], dtype='int32')
            start_time = None
             
        else:
            classifications, times = zip(*pairs)
            classifications = np.array(classifications)
            start_time = times[0]
        
        frame_rate = sample_rate / hop_size

        return (classifications, frame_rate, start_time)
    
    
    def _classify_segment(self, segment, config):
        features, _, time = \
            nfc_classification_utils.get_segment_features(segment, config)
        return (self._segment_classifier.predict([features])[0], time)

        
def _generate_segments(audio, segment_length, hop_size, start_index=0):
    
    samples = audio.samples
    sample_rate = float(audio.sample_rate)
    
    n = len(samples)
    i = start_index
    
    while i + segment_length <= n:
        
        segment = Bunch(
            samples=samples[i:i + segment_length],
            sample_rate=sample_rate,
            start_time=i / sample_rate)
        
        yield segment
        
        i += hop_size
