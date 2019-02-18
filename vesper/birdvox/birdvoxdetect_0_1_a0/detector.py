"""
Module containing Vesper wrapper for BirdVoxDetect NFC detector.

BirdVoxDetect (https://github.com/BirdVox/birdvoxdetect) is an NFC detector
created by the BirdVox project (https://wp.nyu.edu/birdvox/).
"""


import csv
import os.path
import tempfile
import wave

# Uncomment this to use the BirdVoxDetect of the `birdvoxdetect` package
# of the current Conda environment.
# import birdvoxdetect

import numpy as np
import tensorflow as tf


# Uncomment this to use the BirdVoxDetect that is included in the Vesper
# Conda package.
import vesper.birdvox.birdvoxdetect_0_1_a0.birdvoxdetect as birdvoxdetect
import vesper.util.signal_utils as signal_utils


_CLIP_DURATION = .6


class _Detector:
    
    """
    Vesper wrapper for BirdVoxDetect NFC detector.
    
    An instance of this class wraps BirdVoxDetect as a Vesper detector.
    The instance operates on a single audio channel. It accepts a sequence
    of consecutive sample arrays of any sizes via its `detect` method,
    concatenates them in a temporary audio file, and runs BirdVoxDetect
    on the audio file when its `complete_detection` method is called.
    After BirdVoxDetect finishes processing the file, `complete_detection`
    invokes a listener's `process_clip` method for each of the resulting
    clips. The `process_clip` method must accept two arguments, the start
    index and length of the detected clip.
    """
    
    
    def __init__(
            self, threshold, input_sample_rate, listener,
            extra_thresholds=None):
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        tf.logging.set_verbosity(tf.logging.WARN)
        
        self._threshold = threshold
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        self._clip_length = signal_utils.seconds_to_frames(
            _CLIP_DURATION, self._input_sample_rate)
        
        # Create temporary wave file that will be automatically deleted
        # when we close it.
        self._audio_file = tempfile.NamedTemporaryFile(suffix='.wav')
        
        # Create wave file writer, through which we will write to the
        # wave file.
        self._audio_file_writer = WaveFileWriter(
            self._audio_file, 1, self._input_sample_rate)
           

    @property
    def settings(self):
        return self._settings
    
    
    @property
    def input_sample_rate(self):
        return self._input_sample_rate
    
    
    @property
    def listener(self):
        return self._listener
    
    
    def detect(self, samples):
        # print('_Detector.detect {} {}'.format(samples.shape, samples.dtype))
        self._audio_file_writer.write(samples)
 
            
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        # print('_Detector.complete_detection')
        
        # Close wave writer. This ensures that the wave file header and
        # audio data are consistent (particularly the number of frames
        # stored in the header), but does not delete the file.
        self._audio_file_writer.close()
        
        with tempfile.TemporaryDirectory() as output_dir_path:
            
            # output_dir_path = '/Users/harold/Desktop/BirdVoxDetect Output'
            
            audio_file_path = self._audio_file.name
            
            birdvoxdetect.process_file(
                audio_file_path,
                output_dir=output_dir_path,
                threshold=self._threshold)
            
            timestamp_file_path = self._get_timestamp_file_path(
                output_dir_path, audio_file_path)
            
            self._process_timestamps(timestamp_file_path)
                
        # Close wave file. Because it is a temporary file, this will also
        # delete it.
        self._audio_file.close()
        
        self._listener.complete_processing()
        
        
    def _get_timestamp_file_path(self, output_dir_path, audio_file_path):
        
        audio_file_name_base = \
            os.path.splitext(os.path.basename(audio_file_path))[0]
            
        timestamp_file_name = '{}_{}.csv'.format(
            audio_file_name_base, 'timestamps')
        
        return os.path.join(output_dir_path, timestamp_file_name)
    
    
    def _process_timestamps(self, timestamp_file_path):
        
        with open(timestamp_file_path) as timestamp_file:
                
            reader = csv.reader(timestamp_file)
            
            # Skip header
            next(reader)
            
            for row in reader:
                
                peak_time = float(row[1])
                # score = float(row[2])
                
                # Get clip start index from peak time.
                peak_index = signal_utils.seconds_to_frames(
                    peak_time, self._input_sample_rate)
                start_index = peak_index - self._clip_length // 2
                
                # print('processing clip', peak_time, start_index, score)
                
                self._listener.process_clip(start_index, self._clip_length)


class Detector30(_Detector):
    
    """BirdVoxDetect with a threshold of 30."""
    
    extension_name = 'BirdVoxDetect 0.1.a0 30'
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(30, sample_rate, listener, extra_thresholds)


class Detector40(_Detector):
    
    """BirdVoxDetect with a threshold of 40."""
    
    extension_name = 'BirdVoxDetect 0.1.a0 40'
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(40, sample_rate, listener, extra_thresholds)


class Detector50(_Detector):
    
    """BirdVoxDetect with a threshold of 50."""
    
    extension_name = 'BirdVoxDetect 0.1.a0 50'
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(50, sample_rate, listener, extra_thresholds)


class Detector60(_Detector):
    
    """BirdVoxDetect with a threshold of 60."""
    
    extension_name = 'BirdVoxDetect 0.1.a0 60'
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(60, sample_rate, listener, extra_thresholds)


class Detector70(_Detector):
    
    """BirdVoxDetect with a threshold of 70."""
    
    extension_name = 'BirdVoxDetect 0.1.a0 70'
    
    def __init__(self, sample_rate, listener, extra_thresholds=None):
        super().__init__(70, sample_rate, listener, extra_thresholds)


class WaveFileWriter:
    
    """Writes a .wav file one sample array at a time."""
    
    
    def __init__(self, file_, num_channels, sample_rate):
        self._writer = wave.open(file_, 'wb')
        self._writer.setparams((num_channels, 2, sample_rate, 0, 'NONE', None))
        
        
    def write(self, samples):
        
        # Convert samples to wave file dtype if needed.
        if samples.dtype != np.dtype('<i2'):
            samples = np.array(np.round(samples), dtype='<i2')
            
        # Convert samples to raw bytes.
        data = samples.transpose().tostring()
        
        self._writer.writeframes(data)
                
        
    def close(self):
        self._writer.close()
