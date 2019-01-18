import logging
# import time
import wave

import numpy as np
import resampy
import tensorflow as tf

from vesper.util.sample_buffer import SampleBuffer
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier_utils \
    as classifier_utils
import vesper.mpg_ranch.nfc_coarse_classifier_3_0.dataset_utils \
    as dataset_utils
import vesper.util.signal_utils as signal_utils


_TSEEP_SETTINGS = Settings(
    clip_type='Tseep',
    input_chunk_size=3600,
    hop_size=50,
    threshold=.9,
    min_separation=.2,
    initial_clip_padding=.1,
    clip_duration=.4
)

_THRUSH_SETTINGS = Settings(
    clip_type='Thrush',
    input_chunk_size=3600,
    hop_size=50,
    threshold=.9,
    min_separation=.3,
    initial_clip_padding=.2,
    clip_duration=.6
)


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
    
    
    def __init__(self, settings, input_sample_rate, listener):
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        tf.logging.set_verbosity(tf.logging.WARN)
        
        self._settings = settings
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        s2f = signal_utils.seconds_to_frames
        
        s = self._settings
        fs = self._input_sample_rate
        self._input_buffer = None
        self._input_chunk_size = s2f(s.input_chunk_size, fs)
        self._threshold = s.threshold
        self._min_separation = s.min_separation
        self._clip_start_offset = -s2f(s.initial_clip_padding, fs)
        self._clip_length = s2f(s.clip_duration, fs)
        
        self._input_chunk_start_index = 0
        
        self._classifier_settings = self._load_classifier_settings()
        self._estimator = self._create_estimator()
        
        s = self._classifier_settings
        fs = s.waveform_sample_rate
        self._classifier_sample_rate = fs
        self._classifier_waveform_length = s2f(s.waveform_duration, fs)
        fraction = self._settings.hop_size / 100
        self._hop_size = s2f(fraction * s.waveform_duration, fs)
        
#         print(
#             '_Detector.__init__', self.input_sample_rate,
#             self._classifier_sample_rate, self._classifier_waveform_length,
#             self._hop_size, self._clip_start_offset, self._clip_length)
        
        self._open_output_audio_file()
        
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
    
    
    def _load_classifier_settings(self):
        s = self._settings
        path = classifier_utils.get_settings_file_path(s.clip_type)
        logging.info('Loading classifier settings from "{}"...'.format(path))
        return Settings.create_from_yaml_file(path)
        
        
    def _create_estimator(self):
        s = self._settings
        path = classifier_utils.get_tensorflow_model_dir_path(s.clip_type)
        logging.info((
            'Creating TensorFlow estimator from saved model in directory '
            '"{}"...').format(path))
        return tf.contrib.estimator.SavedModelEstimator(str(path))

    
    def _create_dataset(self):
        s = self._classifier_settings
        return dataset_utils.create_spectrogram_dataset_from_waveforms_array(
            self._waveforms, dataset_utils.DATASET_MODE_INFERENCE, s,
            batch_size=64, feature_name=s.model_input_name)
    
    
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
        
#         print((
#             'Processing input chunk of length {} starting at index '
#             '{}...').format(input_length, self._input_chunk_start_index))
        
#         hop_size = signal_utils.get_duration(
#             self._hop_size, self._classifier_sample_rate)
#         print('Hop size is {} seconds.'.format(hop_size))
        
        if self._classifier_sample_rate != self._input_sample_rate:
             
            # print(
            #     'Resampling input chunk from {} Hz to {} Hz...'.format(
            #         self.input_sample_rate, self._classifier_sample_rate))
             
            samples = resampy.resample(
                samples, self._input_sample_rate, self._classifier_sample_rate,
                filter='kaiser_fast')
            
#         print('Resampled chunk has length {}.'.format(len(samples)))

        self._waveforms = _get_analysis_records(
            samples, self._classifier_waveform_length, self._hop_size)
        
#         print('Reshaped chunk has shape {}.'.format(self._waveforms.shape))
        
#         print('Scoring chunk waveforms...')
         
#         start_time = time.time()
         
        scores = classifier_utils.score_dataset_examples(
            self._estimator, self._create_dataset)
        
        self._append_to_output_audio_file(samples, scores)
         
#         elapsed_time = time.time() - start_time
#         num_waveforms = self._waveforms.shape[0]
#         rate = num_waveforms / elapsed_time
#         print((
#             'Scored {} waveforms in {:.1f} seconds, a rate of {:.1f} '
#             'waveforms per second.').format(
#                 num_waveforms, elapsed_time, rate))
        
        peak_indices = self._find_peaks(scores)
        
        self._notify_listener_of_clips(peak_indices, input_length)
        
        self._input_chunk_start_index += input_length
            

    def _find_peaks(self, scores):
        
        if self._min_separation is None:
            min_separation = None
            
        else:
            
            # Get min separation in hops.
            hop_size = signal_utils.get_duration(
                self._hop_size, self._classifier_sample_rate)
            min_separation = self._settings.min_separation / hop_size
        
        peak_indices = signal_utils.find_peaks(
            scores, self._threshold, min_separation)
        
#         print(
#             'Found {} peaks in {} scores.'.format(
#                 len(peak_indices), len(scores)))

        return peak_indices
        
            
    def _notify_listener_of_clips(self, peak_indices, input_length):
        
        # print('Clips:')
        
        start_offset = self._input_chunk_start_index + self._clip_start_offset
        peak_indices *= self._hop_size
        
        for i in peak_indices:
            
            # Convert classification index to input index, accounting
            # for difference between classifier sample rate and input
            # sample rate.
            t = signal_utils.get_duration(i, self._classifier_sample_rate)
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
                
                self._listener.process_clip(
                    clip_start_index, self._clip_length)
        

    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        self._process_input_chunks(process_all_samples=True)
            
        self._listener.complete_processing()
        
        self._close_output_audio_file()


    def _open_output_audio_file(self):
        path = '/Users/harold/Desktop/FLOOD-21C_20170801_220710.wav'
        writer = wave.open(path, 'wb')
        _write_header(writer, 2, self._classifier_sample_rate)
        self._output_audio_file_writer = writer
        self._output_count = 0
        
        
    def _append_to_output_audio_file(self, samples, scores):
        
        if self._output_count >= 0 and self._output_count <= 5:
        
            # Scale scores so their magnitudes are comparable to those
            # of audio samples.
            scores = scores * 10000
            
            # Repeat each score `self._hop_size` times so number of scores
            # equals number of samples.
            scores = scores.reshape((len(scores), 1))
            ones = np.ones((1, self._hop_size))
            scores = (scores * ones).flatten()
            
            # Truncate samples to number of scores.
            samples = samples[:len(scores)]
            
            # Stack samples and scores to make two channels of samples.
            samples = np.vstack((samples, scores))
            
            _write_samples(self._output_audio_file_writer, samples)
        
        self._output_count += 1
        
        
    def _close_output_audio_file(self):
        self._output_audio_file_writer.close()
    
        
# TODO: The wave file code below was copied from
# `vesper.util.audio_file_utils`. We could use a set of utility functions
# for writing wave files in chunks instead of all at once.


_WAVE_SAMPLE_DTYPE = np.dtype('<i2')
 
 
# def write_wave_file(path, samples, sample_rate):
#     num_channels = samples.shape[0]
#     with wave.open(path, 'wb') as writer:
#         _write_header(writer, num_channels, sample_rate)
#         _write_samples(writer, samples)
         
         
def _write_header(writer, num_channels, sample_rate):
     
    sample_size = 2
    sample_rate = int(round(sample_rate))
    length = 0
    compression_type = 'NONE'
    compression_name = 'not compressed'
     
    writer.setparams((
        num_channels, sample_size, sample_rate, length,
        compression_type, compression_name))
     
     
def _write_samples(writer, samples):
     
    num_channels = samples.shape[0]
     
    # Get samples as one-dimensional array.
    if num_channels == 1:
        samples = samples[0]
    else:
        samples = samples.transpose().reshape(-1)
         
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(samples, dtype=_WAVE_SAMPLE_DTYPE)
         
    # Convert samples to string.
    samples = samples.tostring()
     
    # Write to file.
    # This appears to slow down by about an order of magnitude after
    # we archive perhaps a gigabyte of data across hundreds of clips.
    # Not sure why. The slowdown also happens if we open regular files
    # instead of wave files and write samples to them with plain old
    # file_.write(samples).
    # TODO: Write simple test script that writes hundreds of files
    # containing zeros (a million 16-bit integers apiece, say) and
    # see if it is similarly slow. If so, is it slow on Mac OS X?
    # Is it slow on a non-parallels version of Windows? Is it slow
    # if we write the program in C instead of in Python?
    writer.writeframes(samples)


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
    
    
    extension_name = 'MPG Ranch Tseep Detector 0.0'
    
    
    def __init__(self, sample_rate, listener):
        super().__init__(_TSEEP_SETTINGS, sample_rate, listener)

    
class ThrushDetector(_Detector):
     
     
    extension_name = 'MPG Ranch Thrush Detector 0.0'
     
     
    def __init__(self, sample_rate, listener):
        super().__init__(_THRUSH_SETTINGS, sample_rate, listener)
