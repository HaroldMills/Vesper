"""
Module containing Vesper wrapper for BirdVoxDetect NFC detector.

BirdVoxDetect (https://github.com/BirdVox/birdvoxdetect) is an NFC detector
created by the BirdVox project (https://wp.nyu.edu/birdvox/).
"""


import csv
import logging
import os.path
import tempfile
import wave

import numpy as np
import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.open_mp_utils as open_mp_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils


# Uncomment this to use the BirdVoxDetect of the `birdvoxdetect` package
# of the current Python environment.
import birdvoxdetect

# Uncomment this to use the BirdVoxDetect 0.2.0a2 that is included in the
# `vesper` package of the current Python environment.
# import vesper.birdvox.birdvoxdetect_0_2_0_a2.birdvoxdetect as birdvoxdetect


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
    
    
    def __init__(self, input_sample_rate, listener):
        
        open_mp_utils.work_around_multiple_copies_issue()
        
        # Suppress TensorFlow INFO and DEBUG log messages.
        tf.logging.set_verbosity(tf.logging.ERROR)
        
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        self._clip_length = signal_utils.seconds_to_frames(
            _CLIP_DURATION, self._input_sample_rate)
        
        # Create and open temporary wave file. Do not delete
        # automatically on close. We will close the file after we
        # finish writing it, and then BirdVoxDetect will open it
        # again for reading. We delete the file ourselves after
        # BirdVoxDetect finishes processing it.
        self._audio_file = tempfile.NamedTemporaryFile(
            suffix='.wav', delete=False)
        
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
        
        # Close wave writer and wave file.
        self._audio_file_writer.close()
        self._audio_file.close()
        
        with tempfile.TemporaryDirectory() as output_dir_path:
            
            # output_dir_path = '/Users/harold/Desktop/BirdVoxDetect Output'
            
            audio_file_path = self._audio_file.name
            
            birdvoxdetect.process_file(
                audio_file_path,
                bva_threshold=1,
                threshold=self.settings.threshold,
                logger_level=logging.WARN,
                output_dir=output_dir_path)
 
            output_file_path = self._get_output_file_path(
                output_dir_path, audio_file_path)
            
            self._process_detector_output(output_file_path)
                
        os_utils.delete_file(audio_file_path)
        
        self._listener.complete_processing()
        
        
    def _get_output_file_path(self, output_dir_path, audio_file_path):
        
        audio_file_name_base = \
            os.path.splitext(os.path.basename(audio_file_path))[0]
            
        output_file_name = '{}_{}.csv'.format(
            audio_file_name_base, 'checklist')
        
        return os.path.join(output_dir_path, output_file_name)
    
    
    def _process_detector_output(self, output_file_path):
        
        with open(output_file_path) as output_file:
                
            reader = csv.reader(output_file)
            
            # Skip header.
            next(reader)
            
            for row in reader:
                
                # Get clip start index from peak time.
                peak_time = self._parse_time(row[0])
                peak_index = signal_utils.seconds_to_frames(
                    peak_time, self._input_sample_rate)
                start_index = peak_index - self._clip_length // 2
                
                annotations = {}
                
                # Get detector score.
                annotations['Detector Score'] = float(row[2])
                
                # Get classification.
                classification = row[1]
                if classification != 'OTHE':
                    annotations['Classification'] = 'Call.' + classification
                
#                 print(
#                     'processing clip', peak_time, start_index, score,
#                     classification)
                
                self._listener.process_clip(
                    start_index, self._clip_length, annotations=annotations)
                
                
    def _parse_time(self, time):
        parts = time.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    

# The following is untested code to create BirdVoxDetect `_Detector`
# subclasses programmatically when this module is loaded.
#
# 
# def _create_detector_class(threshold_type, threshold):
#     
#     threshold_string = '{:02d}'.format(threshold)
#     
#     class_name = 'Detector{}{}'.format(threshold_type, threshold_string)
#     
#     extension_name = \
#         'BirdVoxDetect 0.1.0 {} {}'.format(threshold_type, threshold_string)
#         
#     threshold_adaptation_enabled = threshold_type == 'AT'
#     
#     settings = Settings(
#         threshold_adaptation_enabled=threshold_adaptation_enabled,
#         threshold=threshold)
#     
#     class_dict = {
#         'extension_name': extension_name,
#         '_settings': settings
#     }
#     
#     cls = type(class_name, (_Detector,), class_dict)
#     
#     globals()[class_name] = cls
#     
#     
# def _create_detector_classes():
#     for threshold_type in ('FT', 'AT'):
#         for threshold in [5, 10, 20, 30, 40, 50, 60, 70, 80, 90]:
#             _create_detector_class(threshold_type, threshold)
#         
#         
# _create_detector_classes()


def _create_ft_settings(threshold):
    return Settings(threshold_adaptation_enabled=False, threshold=threshold)


class DetectorFT05(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 5."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 05'
    _settings = _create_ft_settings(5)


class DetectorFT10(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 10."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 10'
    _settings = _create_ft_settings(10)


class DetectorFT20(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 20."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 20'
    _settings = _create_ft_settings(20)


class DetectorFT30(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 30."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 30'
    _settings = _create_ft_settings(30)


class DetectorFT40(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 40."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 40'
    _settings = _create_ft_settings(40)


class DetectorFT50(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 50."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 50'
    _settings = _create_ft_settings(50)


class DetectorFT60(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 60."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 60'
    _settings = _create_ft_settings(60)


class DetectorFT70(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 70."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 70'
    _settings = _create_ft_settings(70)


class DetectorFT80(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 80."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 80'
    _settings = _create_ft_settings(80)


class DetectorFT90(_Detector):
    
    """BirdVoxDetect with a fixed threshold of 90."""
    
    extension_name = 'BirdVoxDetect 0.2.0a2 FT 90'
    _settings = _create_ft_settings(90)


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
