"""
Module supporting BirdVoxDetect NFC detectors.

When this module is imported, it dynamically creates a detector class
(a subclass of the `_Detector` class of this module) for each BirdVoxDetect
detector in the archive database and adds it to the detector extensions of
this Vesper server.

BirdVoxDetect (https://github.com/BirdVox/birdvoxdetect) is an NFC
detector created by the BirdVox project (https://wp.nyu.edu/birdvox/).
"""


from contextlib import AbstractContextManager
import csv
import logging
import os.path
import tempfile
import wave

import numpy as np

from vesper.django.app.models import Processor
from vesper.util.settings import Settings
import vesper.util.conda_utils as conda_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils


_CLIP_DURATION = .6
_THRESHOLD_TYPES = ('FT', 'AT')


class DetectorError(Exception):
    pass


class _Detector:
    
    """
    Vesper wrapper for BirdVoxDetect NFC detector.
    
    An instance of this class wraps BirdVoxDetect as a Vesper detector.
    The instance operates on a single audio channel. It accepts a sequence
    of consecutive sample arrays of any sizes via its `detect` method,
    concatenates them in a temporary audio file, and runs BirdVoxDetect
    on the audio file when its `complete_detection` method is called.
    BirdVoxDetect is run in its own Conda environment, which can be
    different from the Conda environment in which the Vesper server is
    running. After BirdVoxDetect finishes processing the file,
    `complete_detection` invokes a listener's `process_clip` method for
    each of the resulting clips. The `process_clip` method must accept
    three arguments: the start index and length of the detected clip,
    and a dictionary of annotations for the clip.
    """
    
    
    def __init__(self, input_sample_rate, listener):
        
        self._input_sample_rate = input_sample_rate
        self._listener = listener
        
        self._clip_length = signal_utils.seconds_to_frames(
            _CLIP_DURATION, self._input_sample_rate)
        
        # Create and open temporary audio file. Do not delete
        # automatically on close. We will close the file after we
        # finish writing it, and then BirdVoxDetect will open it
        # again for reading. We delete the file ourselves after
        # BirdVoxDetect finishes processing it.
        self._audio_file = tempfile.NamedTemporaryFile(
            suffix='.wav', delete=False)
        
        # Create audio file writer.
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
        self._audio_file_writer.write(samples)
    
    
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        # Close audio file writer and audio file.
        self._audio_file_writer.close()
        self._audio_file.close()
        
        audio_file_path = self._audio_file.name
        
        with tempfile.TemporaryDirectory() as output_dir_path, \
                FileDeleter(audio_file_path):
            
            settings = self.settings
            
            module_name = 'vesper_birdvox.run_birdvoxdetect'
            
            # Build list of command line arguments.
            threshold = str(settings.threshold)
            audio_file_path = self._audio_file.name
            args = (
                '--threshold', threshold,
                '--output-dir', output_dir_path,
                audio_file_path)
            if settings.threshold_adaptive:
                args = ('--threshold-adaptive',) + args
            
            environment_name = f'birdvoxdetect-{settings.detector_version}'
            
            try:
                results = conda_utils.run_python_script(
                    module_name, args, environment_name)
            
            except Exception as e:
                raise DetectorError(
                    f'Could not run {self.extension_name} in Conda '
                    f'environment "{environment_name}". Error message '
                    f'was: {str(e)}')
            
            self._log_bvd_results(results)
            
            if results.returncode != 0:
                # BVD process completed abnormally
                
                raise DetectorError(
                    f'{self.extension_name} process completed abnormally. '
                    f'See above log messages for details.')
            
            else:
                # BVD process completed normally
                
                detection_file_path = self._get_detection_file_path(
                    output_dir_path, audio_file_path)
                self._process_detection_file(detection_file_path)
    
    
    def _log_bvd_results(self, results):
        
        if results.returncode != 0:
            # BVD process completed abnormally.
            
            logging.info(
                f'        {self.extension_name} process completed '
                f'abnormally with return code {results.returncode}. '
                f'No clips will be created.')
        
        else:
            # BVD process completed normally
            
            logging.info(
                f'        {self.extension_name} process completed normally.')
        
        self._log_bvd_output_stream(results.stdout, 'standard output')
        self._log_bvd_output_stream(results.stderr, 'standard error')
    
    
    def _log_bvd_output_stream(self, stream_text, stream_name):
        
        if len(stream_text) == 0:
            
            logging.info(
                f'        {self.extension_name} process {stream_name} '
                f'was empty.')
        
        else:
            
            logging.info(
                f'        {self.extension_name} process {stream_name} was:')
            
            lines = stream_text.strip().splitlines()
            for line in lines:
                logging.info(f'            {line}')
    
    
    def _get_detection_file_path(self, output_dir_path, audio_file_path):
        
        audio_file_name_base = \
            os.path.splitext(os.path.basename(audio_file_path))[0]
            
        detection_file_name = \
            f'{audio_file_name_base}_detections_for_vesper.csv'
        
        return os.path.join(output_dir_path, detection_file_name)
    
    
    def _process_detection_file(self, detection_file_path):
        
        with open(detection_file_path, newline='') as detection_file:
            
            reader = csv.reader(detection_file)
            
            # Skip header.
            header = next(reader)
            column_count = len(header)
            
            for row in reader:
                
                start_index = self._get_clip_start_index(row[0])
                
                # Create dictionary of annotations for this clip,
                # ignoring missing values.
                annotations = dict(
                    (header[i], row[i])
                    for i in range(1, column_count)
                    if row[i] != '')
                
                self._listener.process_clip(
                    start_index, self._clip_length, annotations=annotations)
        
        self._listener.complete_processing()
    
    
    def _get_clip_start_index(self, center_time):
        center_time = float(center_time)
        center_index = signal_utils.seconds_to_frames(
            center_time, self._input_sample_rate)
        return center_index - self._clip_length // 2


class FileDeleter(AbstractContextManager):
    
    def __init__(self, file_path):
        self._file_path = file_path
    
    def __exit__(self, exception_type, exception_value, traceback):
        os_utils.delete_file(self._file_path)


_detector_classes = None


def get_detector_classes():
    
    """
    Gets the BirdVoxDetector detector classes for this archive.
    
    The classes are created the first time this method is called, with
    one class for each BirdVoxDetect detector in the archive database.
    """
    
    global _detector_classes
    
    if _detector_classes is None:
        # have not yet created detector classes
        
        _detector_classes = _create_detector_classes()
    
    return _detector_classes


def _create_detector_classes():
    
    detectors = Processor.objects.filter(type='Detector')
    bvd_detectors = detectors.filter(name__startswith='BirdVoxDetect')
    detector_classes = []
    
    for detector in bvd_detectors:
        
        try:
            cls = _create_detector_class(detector)
        
        except Exception as e:
            logging.warning(
                f'Could not create detector "{detector.name}". '
                f'Error message was: {str(e)}')
        
        else:
            detector_classes.append(cls)
    
    return detector_classes


def _create_detector_class(processor):
    
    detector_version, threshold_type, threshold = \
        _parse_detector_name(processor.name)
    
    # Get detector version with an underscore instead of a string,
    # but keep the original version since we'll need that, too.
    detector_version_ = detector_version.replace('.', '_')
    
    threshold_adaptive = threshold_type == 'AT'
    
    threshold_string = f'{threshold:02d}'
    
    class_name = \
        f'Detector_{detector_version_}_{threshold_type}_{threshold_string}'
    
    extension_name = \
        f'BirdVoxDetect {detector_version} {threshold_type} {threshold_string}'
    
    settings = Settings(
        detector_version=detector_version,
        threshold_adaptive=threshold_adaptive,
        threshold=threshold)
    
    class_dict = {
        'extension_name': extension_name,
        '_settings': settings
    }
    
    return type(class_name, (_Detector,), class_dict)


def _parse_detector_name(name):
    
    parts = name.split()
    
    if len(parts) != 4:
        raise ValueError(
            f'Name must be of the form "BirdVoxDetect <version> <type> '
            f'<threshold>", for example "BirdVoxDetect 0.5.0 FT 30".')
    
    detector_version = parts[1]
    
    threshold_type = parts[2]
    
    if threshold_type not in _THRESHOLD_TYPES:
        raise ValueError(
            f'Unrecognized detection threshold type "{threshold_type}". '
            f'The threshold type must be either "FT" or "AT".')
    
    try:
        threshold = int(parts[3])
    except Exception:
        raise ValueError(
            f'Bad detection threshold "{parts[3]}". The threshold must '
            f'be a number in the range [0, 100].')
    
    return detector_version, threshold_type, threshold


class WaveFileWriter:
    
    """Writes a .wav file one sample array at a time."""
    
    
    def __init__(self, file_, num_channels, sample_rate):
        self._writer = wave.open(file_, 'wb')
        self._writer.setparams((num_channels, 2, sample_rate, 0, 'NONE', None))
    
    
    def write(self, samples):
        
        # Convert samples to wave file dtype if needed.
        if samples.dtype != np.dtype('<i2'):
            samples = np.array(np.round(samples), dtype='<i2')
        
        # Convert samples to bytes.
        data = samples.transpose().tobytes()
        
        self._writer.writeframes(data)
    
    
    def close(self):
        self._writer.close()
