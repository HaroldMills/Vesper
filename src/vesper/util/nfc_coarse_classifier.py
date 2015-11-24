"""Module containing class `NfcCoarseClassifier`."""


import cPickle as pickle
import os.path
import random

import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.spectrogram import Spectrogram
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


def create_classifier(classifier_name):

    package_dir_path = os.path.dirname(__file__)
    file_name = '{} Coarse Classifier.pkl'.format(classifier_name)
    file_path = os.path.join(package_dir_path, file_name)

    # TODO: Handle load errors.
    with open(file_path, 'r') as file_:
        return pickle.load(file_)


def extract_clip_segment(
        clip, segment_duration, segment_source, source_duration=None):
    
    source = _get_segment_source(clip, segment_source, source_duration)
    
    if source is None:
        return None
    
    else:
        
        source_start_index, source_length = source
        
        sample_rate = clip.sound.sample_rate
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
            samples = clip.sound.samples[start_index:end_index]
            
            return Bunch(
                samples=samples,
                sample_rate=clip.sound.sample_rate,
                start_index=start_index)



def _get_segment_source(clip, segment_source, source_duration):
    
    source = segment_source
    clip_length = len(clip.sound.samples)
    
    if source == SEGMENT_SOURCE_CLIP:
        return (0, clip_length)
        
    elif source == SEGMENT_SOURCE_CLIP_CENTER:
        
        sample_rate = clip.sound.sample_rate
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
        classifications, _, _ = self.classify_clip_segments(clip)
        if np.any(classifications == 1):
            return 1.
        else:
            return 0.
    
    
    def classify_clip_segments(self, clip):
        
        sound = clip.sound
        c = self._config
        
        u = signal_utils
        sample_rate = sound.sample_rate
        segment_length = u.seconds_to_frames(c.segment_duration, sample_rate)
        hop_size = u.seconds_to_frames(c.segment_hop_size, sample_rate)
        
        pairs = [self._classify_segment(s, c)
                 for s in _generate_segments(sound, segment_length, hop_size)]
        
        classifications, times = zip(*pairs)
        frame_rate = sound.sample_rate / hop_size
        start_time = times[0]
        
        return (np.array(classifications), frame_rate, start_time)
    
    
    def _classify_segment(self, segment, config):
        features, _, time = get_segment_features(segment, config)
        return (self._segment_classifier.predict(features)[0], time)

        
def _generate_segments(sound, segment_length, hop_size, start_index=0):
    
    samples = sound.samples
    sample_rate = float(sound.sample_rate)
    
    n = len(samples)
    i = start_index
    
    while i + segment_length <= n:
        
        segment = Bunch(
            samples=samples[i:i + segment_length],
            sample_rate=sample_rate,
            start_time=i / sample_rate)
        
        yield segment
        
        i += hop_size


def get_segment_features(segment, config):
    
    c = config
    
    spectrogram = Spectrogram(segment, c.spectrogram_params)
    spectra = spectrogram.spectra
    
    # Clip spectra to specified power range.
    spectra.clip(config.min_power, config.max_power)
    
    # Remove portions of spectra outside of specified frequency range.
    sample_rate = segment.sample_rate
    dft_size = c.spectrogram_params.dft_size
    start_index = _freq_to_index(c.min_freq, sample_rate, dft_size)
    end_index = _freq_to_index(c.max_freq, sample_rate, dft_size) + 1
    spectra = spectra[:, start_index:end_index]
    
    # TODO: Should summing happen before logs are taken?
    # TODO: Consider parameterizing the pooling operation, and offering
    # at least averaging and max.
    spectra = _sum_adjacent(spectra, c.pooling_block_size)
    
    # TODO: Make each signal processing operation produce a correct time
    # calibration for each of its outputs, calculated according to the
    # time calibrations of its inputs and the signal processing operation
    # performed. Support both seconds and date/time calibrations.
    #
    # A small number of utility functions that perform time calibration
    # transformations should cover the vast majority of cases.
    #
    # It may be advantageous to maintain the date/time portion of
    # calibrations separately from the seconds portions. For example,
    # a calibration might comprise a start offset in seconds (zero by
    # default), a frame rate in frames per second (one by default),
    # and a start date/time (none by default). Then most or all of
    # the transformations that we might need could operate only on
    # the offset and frame rate. This would help maintain precision
    # since date/time data structures are often not as precise as
    # times in double precision seconds. Python's datetime class,
    # for example, keeps time only to the nearest microsecond.
    
    # Compute time of features from times of spectra.
    times = spectrogram.times
    n = len(spectra) * c.pooling_block_size[0]
    time = (times[0] + times[n - 1]) / 2.
    
    features = _normalize(spectra.flatten())
    
    # For a training set of about 9000 MPG Ranch call and noise segments
    # (roughly half call segments and half noise segments), including the
    # segment spectrogram norm did not yield a classifier that was as
    # good as the one gotten when we did not include the norm. However,
    # learning curves suggested that the classifier that included the
    # norm might be superior if trained on a larger number of examples.
    # The learning curve for features that did not include the norm rose
    # more quickly than the learning curve for features that did include
    # the norm, but also leveled off more, so that it looked like the
    # latter might eventually overtake the former.
    if c.include_norm_in_features:
        norm = np.linalg.norm(spectra)
        features = np.hstack([features, norm])
    
    return (features, spectra, time)


def _freq_to_index(freq, sample_rate, dft_size):
    bin_size = sample_rate / dft_size
    return int(round(freq / bin_size))


def _sum_adjacent(x, (m, n)):
    
    xm, xn = x.shape
    
    xm = (xm // m) * m
    xn = (xn // n) * n
    x = x[:xm, :xn]
    
    # Sum columns.
    x.shape = (xm, xn / n, n)
    x = x.sum(2)
    xn /= n
    
    # Sum rows.
    x = x.transpose()
    x.shape = (xn, xm / m, m)
    x = x.sum(2)
    x = x.transpose()
    
    return x
    
    
def _test_sum_adjacent():
    x = np.arange(24)
    x.shape = (4, 6)
    print(x)
    x = _sum_adjacent(x, 2, 3)
    print(x)


def _normalize(x):
    norm = np.linalg.norm(x)
    return x / norm if norm != 0 else x
