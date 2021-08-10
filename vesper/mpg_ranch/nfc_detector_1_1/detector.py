"""
Module containing MPG Ranch nocturnal flight call (NFC) detector.

The detector looks for NFCs in a single audio input channel by scoring
a sequence of input records, producing a clip when the score rises above
a threshold. The input records typically overlap. For each input record,
the detector computes a spectrogram and applies a convolutional neural
network to the spectrogram to obtain a score.

The `TseepDetector` and `ThrushDetector` classes of this module are
configured to detect tseep and thrush NFCs, respectively.

The detectors of this module use the classifiers of the
`vesper.mpg_ranch.nfc_coarse_classifier_4_1` package for
distinguishing audio segments that contain NFCs from segments that
do not.

When run on 17 nights of recordings made in Ithaca, NY from 2021-04-03
through 2021-04-19 the detectors of this module produced the same
clips as those produced by the corresponding detectors of the
`vesper.mpg_ranch.nfc_detector_1_0` module. The detectors of this
module were run with TensorFlow 2.5.0rc1 and the detectors of the
other module with TensorFlow 1.15.5. Each of the thrush detectors
produced 12094 clips and each of the tseep detectors produced 5476
clips. The clips produced by corrseponding detectors had exactly the
same start indices and lengths, and the scores (on a scale of 0 to 100)
of the clips of each matching pair differed by less than .001.
"""


import logging
# import time

import numpy as np
import tensorflow as tf

from vesper.util.detection_score_file_writer import DetectionScoreFileWriter
from vesper.util.sample_buffer import SampleBuffer
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_4_1.classifier_utils \
    as classifier_utils
import vesper.mpg_ranch.nfc_coarse_classifier_4_1.dataset_utils \
    as dataset_utils
import vesper.signal.resampling_utils as resampling_utils
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.signal_utils as signal_utils


# TODO: Consider specifying threshold on a scale from 0 to 100 rather
# than on a scale from 0 to 1, since that's how scores are presented
# in the UI.


_TSEEP_SETTINGS = Settings(
    clip_type='Tseep',
    input_chunk_size=3600,
    hop_size=50,
    threshold=.41,
    initial_clip_padding=.1,
    clip_duration=.4
)

_THRUSH_SETTINGS = Settings(
    clip_type='Thrush',
    input_chunk_size=3600,
    hop_size=50,
    threshold=.70,
    initial_clip_padding=.2,
    clip_duration=.6
)


_DETECTOR_SAMPLE_RATE = 24000


# Constants controlling detection score output. The output is written to
# a stereo audio file with detector audio input samples in one channel
# and detection scores in the other. It is useful for detector debugging,
# but should be disabled in production.
_SCORE_OUTPUT_ENABLED = False
_SCORE_FILE_PATH_FORMAT = '/Users/harold/Desktop/{} Detector Scores.wav'
_SCORE_OUTPUT_START_OFFSET = 3600   # seconds
_SCORE_OUTPUT_DURATION = 1000       # seconds
_SCORE_SCALE_FACTOR = 10000


class _Detector:
    
    """
    MPG Ranch NFC detector.
    
    An instance of this class operates on a single audio channel. It has a
    `detect` method that takes a NumPy array of samples. The method can be
    called repeatedly with consecutive sample arrays. The `complete_detection`
    method should be called after the final call to the `detect` method.
    During detection, each time the detector detects a clip it notifies
    a listener by invoking the listener's `process_clip` method. The
    `process_clip` method must accept two arguments, the start index and
    length of the detected clip.
    
    See the `_TSEEP_SETTINGS` and `_THRUSH_SETTINGS` objects above for
    settings that make a `_Detector` detect higher-frequency and
    lower-frequency NFCs, respectively, using the MPG Ranch tseep and
    thrush coarse classifiers. The `TseepDetector` and `ThrushDetector`
    classes of this module subclass the `_Detector` class with fixed
    settings, namely `_TSEEP_SETTINGS` and  `_THRUSH_SETTINGS`, respectively.
    """
    
    
    def __init__(
            self, settings, input_sample_rate, listener,
            extra_thresholds=None):
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        logging.getLogger('tensorflow').setLevel(logging.WARN)
        
        self._settings = settings
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        s2f = signal_utils.seconds_to_frames
        
        s = self._settings
        fs = self._input_sample_rate
        self._input_buffer = None
        self._input_chunk_size = s2f(s.input_chunk_size, fs)
        self._thresholds = self._get_thresholds(extra_thresholds)
        self._clip_start_offset = -s2f(s.initial_clip_padding, fs)
        self._clip_length = s2f(s.clip_duration, fs)
        
        self._input_chunk_start_index = 0
        
        self._classifier_settings = self._load_classifier_settings()
        self._model = self._load_model()
        
        s = self._classifier_settings
        
        if s.waveform_sample_rate != _DETECTOR_SAMPLE_RATE:
            raise ValueError((
                'Classifier neural network sample rate is {} Hz rather '
                'than the expected {} Hz.').format(
                    s.waveform_sample_rate, _DETECTOR_SAMPLE_RATE))
            
        fs = s.waveform_sample_rate
        self._classifier_sample_rate = fs
        self._classifier_waveform_length = s2f(s.waveform_duration, fs)
        fraction = self._settings.hop_size / 100
        self._hop_size = s2f(fraction * s.waveform_duration, fs)
        
        if _SCORE_OUTPUT_ENABLED:
            file_path = _SCORE_FILE_PATH_FORMAT.format(settings.clip_type)
            self._score_file_writer = DetectionScoreFileWriter(
                file_path, self._input_sample_rate, _SCORE_SCALE_FACTOR,
                self._hop_size, _SCORE_OUTPUT_START_OFFSET,
                _SCORE_OUTPUT_DURATION)
        
#         settings = self._classifier_settings.__dict__
#         names = sorted(settings.keys())
#         for name in names:
#             print('{}: {}'.format(name, settings[name]))
        
        
    @property
    def settings(self):
        return self._settings
    
    
    @property
    def input_sample_rate(self):
        return self._input_sample_rate
    
    
    @property
    def listener(self):
        return self._listener
    
    
    def _get_thresholds(self, extra_thresholds):
        thresholds = set([self._settings.threshold])
        if extra_thresholds is not None:
            thresholds |= set(extra_thresholds)
        return sorted(thresholds)
    
    
    def _load_classifier_settings(self):
        s = self._settings
        path = classifier_utils.get_settings_file_path(s.clip_type)
        logging.info('Loading classifier settings from "{}"...'.format(path))
        return Settings.create_from_yaml_file(path)
        
        
    def _load_model(self):
        s = self._settings
        path = classifier_utils.get_keras_model_file_path(s.clip_type)
        logging.info(f'Loading classifier model from "{path}"...')
        return tf.keras.models.load_model(path)

    
    def detect(self, samples):
        
        if self._input_buffer is None:
            self._input_buffer = SampleBuffer(samples.dtype)
             
        self._input_buffer.write(samples)
        
        self._process_input_chunks()
            
            
    def _process_input_chunks(self, process_all_samples=False):
        
        # Process as many chunks of input samples of size
        # `self._input_chunk_size` as possible.
        while len(self._input_buffer) >= self._input_chunk_size:
            chunk = self._input_buffer.read(self._input_chunk_size)
            self._process_input_chunk(chunk)
            
        # If indicated, process any remaining input samples as one chunk.
        # The size of the chunk will differ from `self._input_chunk_size`.
        if process_all_samples and len(self._input_buffer) != 0:
            chunk = self._input_buffer.read()
            self._process_input_chunk(chunk)
            
            
    def _process_input_chunk(self, samples):
        
        input_length = len(samples)
        
        if self._classifier_sample_rate != self._input_sample_rate:
            # need to resample input
            
            # When the input sample rate is 22050 Hz or 44100 Hz,
            # we resample as though it were 22000 Hz or 44000 Hz,
            # respectively, resulting in an actual resampled rate of
            # about 24055 Hz rather than 24000 Hz. This allows us to
            # resample much faster, and has little or no effect on the
            # clips [NEED TO SHOW THIS] output by the detector, since
            # the change to the resampled rate is small (only about a
            # quarter of a percent), and the detector is fairly
            # insensitive to small changes in the frequency and duration
            # of NFCs. We account for such sample rate substitutions
            # when computing the start index in the input signal of a
            # detected clip in the `_notify_listener_of_clips` method,
            # below.
            #
            # The lack of rigor inherent in this trick will always make
            # the processing of 22050 Hz and 44100 Hz input a little
            # questionable. In the future, I hope to obviate the trick by
            # implementing faster but proper resampling of 22050 Hz and
            # 44100 Hz input. 
            if self._input_sample_rate == 22050:
                self._purported_input_sample_rate = 22000
            elif self._input_sample_rate == 44100:
                self._purported_input_sample_rate = 44000
            else:
                self._purported_input_sample_rate = self._input_sample_rate
             
            # start_time = time.time()
            
            samples = resampling_utils.resample_to_24000_hz(
                samples, self._purported_input_sample_rate)
            
            # processing_time = time.time() - start_time
            # input_duration = input_length / self._input_sample_rate
            # rate = input_duration / processing_time
            # print((
            #     'Resampled {:.1f} seconds of input in {:.1f} seconds, '
            #     'or {:.1f} times faster than real time.').format(
            #         input_duration, processing_time, rate))
            
        else:
            # don't need to resample input
            
            self._purported_input_sample_rate = self._input_sample_rate
            
        self._waveforms = _get_analysis_records(
            samples, self._classifier_waveform_length, self._hop_size)
        
#         print('Scoring chunk waveforms...')
#         start_time = time.time()
         
        s = self._classifier_settings
        dataset = \
            dataset_utils.create_spectrogram_dataset_from_waveforms_array(
                self._waveforms, dataset_utils.DATASET_MODE_INFERENCE, s,
                batch_size=64, feature_name=s.model_input_name)

        scores = self._model.predict(dataset).flatten()
            
#         elapsed_time = time.time() - start_time
#         num_waveforms = self._waveforms.shape[0]
#         rate = num_waveforms / elapsed_time
#         print((
#             'Scored {} waveforms in {:.1f} seconds, a rate of {:.1f} '
#             'waveforms per second.').format(
#                 num_waveforms, elapsed_time, rate))
        
        if _SCORE_OUTPUT_ENABLED:
            self._score_file_writer.write(samples, scores)
         
        for threshold in self._thresholds:
            peak_indices = signal_utils.find_peaks(scores, threshold)
            peak_scores = scores[peak_indices]
            self._notify_listener_of_clips(
                peak_indices, peak_scores, input_length, threshold)
        
        self._input_chunk_start_index += input_length
            

    def _notify_listener_of_clips(
            self, peak_indices, peak_scores, input_length, threshold):
        
        # print('Clips:')
        
        start_offset = self._input_chunk_start_index + self._clip_start_offset
        peak_indices *= self._hop_size
        
        for i, score in zip(peak_indices, peak_scores):
            
            # Convert classification index to input index, accounting for
            # any difference between classification sample rate and input
            # rate.
            f = self._input_sample_rate / self._purported_input_sample_rate
            classification_sample_rate = f * self._classifier_sample_rate
            t = signal_utils.get_duration(i, classification_sample_rate)
            i = signal_utils.seconds_to_frames(t, self._input_sample_rate)
            
            clip_start_index = i + start_offset
            clip_end_index = clip_start_index + self._clip_length
            chunk_end_index = self._input_chunk_start_index + input_length
            
            if clip_start_index < 0:
                logging.warning(
                    'Rejected clip that started before beginning of '
                    'recording.')
                
            elif clip_end_index > chunk_end_index:
                # clip might extend past end of recording, since it extends
                # past the end of this chunk (we do not know whether or
                # not the current chunk is the last)
                
                logging.warning(
                    'Rejected clip that ended after end of recording chunk.')
                
            else:
                # all clip samples are in the recording interval extending
                # from the beginning of the recording to the end of the
                # current chunk
                
                # print(
                #     '    {} {}'.format(clip_start_index, self._clip_length))
                
                annotations = {'Detector Score': 100 * score}
                
                self._listener.process_clip(
                    clip_start_index, self._clip_length, threshold,
                    annotations)
        

    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        self._process_input_chunks(process_all_samples=True)
            
        self._listener.complete_processing()
        
        if _SCORE_OUTPUT_ENABLED:
            self._score_file_writer.close()


# TODO: The following two functions were copied from
# vesper.util.time_frequency_analysis_utils. They should probably both
# be public, and in a more general-purpose module.


def _get_analysis_records(samples, record_size, hop_size):

    """
    Creates a sequence of hopped sample records from the specified samples.

    This method uses a NumPy array stride trick to create the desired
    sequence as a view of the input samples that can be created at very
    little cost. The caveat is that the view should only be read from,
    and never written to, since when the hop size is less than the
    record size the view's records overlap in memory.

    The trick is from the `_fft_helper` function of the
    `scipy.signal.spectral` module of SciPy.
    """

    # Get result shape.
    num_samples = samples.shape[-1]
    num_vectors = _get_num_analysis_records(num_samples, record_size, hop_size)
    shape = samples.shape[:-1] + (num_vectors, record_size)

    # Get result strides.
    stride = samples.strides[-1]
    strides = samples.strides[:-1] + (hop_size * stride, stride)

    return np.lib.stride_tricks.as_strided(samples, shape, strides)


def _get_num_analysis_records(num_samples, record_size, hop_size):

    if record_size <= 0:
        raise ValueError('Record size must be positive.')

    elif hop_size <= 0:
        raise ValueError('Hop size must be positive.')

    elif hop_size > record_size:
        raise ValueError('Hop size must not exceed record size.')

    if num_samples < record_size:
        # not enough samples for any records

        return 0

    else:
        # have enough samples for at least one record

        overlap = record_size - hop_size
        return (num_samples - overlap) // hop_size


class TseepDetector(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(
            _TSEEP_SETTINGS, sample_rate, listener, extra_thresholds)

    
def _tseep_settings(threshold, hop_size=50):
    return Settings(
        _TSEEP_SETTINGS,
        threshold=threshold / 100,
        hop_size=hop_size)


def _thrush_settings(threshold, hop_size=50):
    return Settings(
        _THRUSH_SETTINGS,
        threshold=threshold / 100,
        hop_size=hop_size)


class TseepDetector90(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 90'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(90)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector80(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 80'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(80)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector70(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 70'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(70)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector60(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 60'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(60)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector60_25(_Detector):
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 60 25'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(60, 25)
        super().__init__(settings, sample_rate, listener, extra_thresholds)


class TseepDetector60_12(_Detector):
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 60 12.5'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(60, 12.5)
        super().__init__(settings, sample_rate, listener, extra_thresholds)


class TseepDetector50(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 50'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(50)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector40(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 40'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(40)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector30(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 30'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(30)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class TseepDetector20(_Detector):
    
    
    extension_name = 'MPG Ranch Tseep Detector 1.1 20'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _tseep_settings(20)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector(_Detector):
     
     
    extension_name = 'MPG Ranch Thrush Detector 1.1'
     
     
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(
            _THRUSH_SETTINGS, sample_rate, listener, extra_thresholds)


class ThrushDetector90(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 90'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(90)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector80(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 80'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(80)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector70(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 70'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(70)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector70_25(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 70 25'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(70, 25)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector70_12(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 70 12.5'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(70, 12.5)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector60(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 60'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(60)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector50(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 50'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(50)
        super().__init__(settings, sample_rate, listener, extra_thresholds)

    
class ThrushDetector40(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 40'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(40)
        super().__init__(settings, sample_rate, listener, extra_thresholds)


class ThrushDetector30(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 30'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(30)
        super().__init__(settings, sample_rate, listener, extra_thresholds)


class ThrushDetector20(_Detector):
    
    
    extension_name = 'MPG Ranch Thrush Detector 1.1 20'
    
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        settings = _thrush_settings(20)
        super().__init__(settings, sample_rate, listener, extra_thresholds)
