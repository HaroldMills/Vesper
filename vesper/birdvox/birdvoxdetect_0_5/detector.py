"""
Module containing Vesper wrapper for BirdVoxDetect 0.5.x NFC detector.

BirdVoxDetect (https://github.com/BirdVox/birdvoxdetect) is an NFC detector
created by the BirdVox project (https://wp.nyu.edu/birdvox/).
"""


import csv
import logging
import os.path
import tempfile
import wave

import numpy as np

from vesper.util.settings import Settings
import vesper.util.conda_utils as conda_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils


# TODO: Modify detector infrastructure so Vesper can support new versions
# of BirdVoxDetect as they appear, without modification, as long as the
# BirdVoxDetect checklist file format does not change.

# TODO: Consider auto-generating classes for various BVD versions and
# adding them to the extension manager on startup according to the
# BirdVoxDetect processors in the archive database. We could require
# that BirdVoxDetect processor names be in a particular format, e.g.
# BirdVoxDetect 0.5.0 AT 30, and parse the names to determine the
# classes to create.

# TODO: Include optional map from BVD version numbers to Conda environment
# names in preferences?


_DETECTOR_VERSIONS = ('0.5.0',)

# TODO: Could clip duration be a preference?
_CLIP_DURATION = .6


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
        
        # Create and open temporary wave file. Do not delete
        # automatically on close. We will close the file after we
        # finish writing it, and then BirdVoxDetect will open it
        # again for reading. We delete the file ourselves after
        # BirdVoxDetect finishes processing it.
        self._audio_file = tempfile.NamedTemporaryFile(
            suffix='.wav', delete=False)
        
        # Create wave file writer, with which we will write to the wave file.
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
    
    
#     def _check_bvd_version(self):
#         
#         version = birdvoxdetect.__version__
#         
#         # Get major and minor version numbers.
#         parts = version.split('.')
#         try:
#             major = int(parts[0])
#             minor = int(parts[1])
#         except Exception:
#             self._handle_incompatible_bvd_version(version)
#             
#         if not (major == 0 and minor == 2):
#             self._handle_incompatible_bvd_version(version)
#     
#     
#     def _handle_incompatible_bvd_version(self, version):
#         raise ValueError(
#             f'Installed BirdVoxDetect version {version} is not '
#             'compatible with this detector wrapper. The wrapper '
#             'only works with BirdVoxDetect versions in the 0.2.x '
#             'family.')
    
    
    def detect(self, samples):
        self._audio_file_writer.write(samples)
    
    
    def complete_detection(self):
        
        """
        Completes detection after the `detect` method has been called
        for all input.
        """
        
        # Close wave writer and wave file.
        self._audio_file_writer.close()
        self._audio_file.close()
        
        with tempfile.TemporaryDirectory() as output_dir_path:
            
            settings = self.settings
            
            module_name = 'birdvoxdetect'
            
            # Build list of command line arguments.
            threshold = str(settings.threshold)
            audio_file_path = self._audio_file.name
            args = (
                '--threshold', threshold,
                '--output-dir', output_dir_path,
                audio_file_path)
            
            environment_name = f'birdvoxdetect-{settings.detector_version}'
            
            try:
                results = conda_utils.run_python_script(
                    module_name, args, environment_name)
            
            except Exception as e:
                raise DetectorError(
                    f'Could not run birdvoxdetect in Conda environment '
                    f'"{environment_name}". Error message was: {str(e)}')
            
            self._log_bvd_process_results(results)
            
            checklist_file_path = self._get_checklist_file_path(
                output_dir_path, audio_file_path)
            
            self._process_checklist_file(checklist_file_path)
        
        os_utils.delete_file(audio_file_path)
        
        self._listener.complete_processing()
    
    
    def _log_bvd_process_results(self, results):
        
        logging.info(
            f'        BirdVoxDetect process completed with return code '
            f'{results.returncode}.')
        
        self._log_bvd_output_stream(results.stdout, 'standard output')
        self._log_bvd_output_stream(results.stderr, 'standard error')
    
    
    def _log_bvd_output_stream(self, stream_text, stream_name):
        
        if len(stream_text) == 0:
            
            logging.info(
                f'        BirdVoxDetect process {stream_name} was empty.')
            
        else:
            
            logging.info(
                f'        BirdVoxDetect process {stream_name} was:')
            
            lines = stream_text.strip().splitlines()
            for line in lines:
                logging.info(f'            {line}')


    def _get_checklist_file_path(self, output_dir_path, audio_file_path):
        
        audio_file_name_base = \
            os.path.splitext(os.path.basename(audio_file_path))[0]
            
        checklist_file_name = f'{audio_file_name_base}_checklist.csv'
        
        return os.path.join(output_dir_path, checklist_file_name)
    
    
    def _process_checklist_file(self, checklist_file_path):
        
        with open(checklist_file_path) as checklist_file:
                
            reader = csv.reader(checklist_file)
            
            # Skip header.
            header = next(reader)
            column_count = len(header)
            
            if column_count == 3:
                self._process_checklist_file_0(reader)
            if column_count == 5:
                self._process_checklist_file_1(reader)
            else:
                self._process_checklist_file_2(reader)
    
    
    def _process_checklist_file_0(self, reader):
        
        """Processes a three-column BirdVoxDetect checklist file."""
        
        for row in reader:
            
            # Get clip start index from peak time.
            start_index = self._get_clip_start_index(row[0])
            classification = row[1]
            detector_score = float(row[2])
            
            annotations = {}
            
            if classification != 'OTHE':
                annotations['Classification'] = 'Call.' + classification
            
            annotations['Detector Score'] = detector_score
            
            self._listener.process_clip(
                start_index, self._clip_length, annotations=annotations)
    
    
    def _get_clip_start_index(self, peak_time_string):
        peak_time = self._parse_time(peak_time_string)
        peak_index = signal_utils.seconds_to_frames(
            peak_time, self._input_sample_rate)
        return peak_index - self._clip_length // 2
    
    
    def _parse_time(self, time):
        parts = time.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    
    def _process_checklist_file_1(self, reader):
        
        """Processes a five-column BirdVoxDetect checklist file."""
        
        for row in reader:
            
            start_index = self._get_clip_start_index(row[0])
            species_code = row[1]
            family_name = row[2]
            order_name = _get_order_name(row[3])
            detector_score = float(row[4])

            annotations = {}
            
            annotations['BirdVoxClassify Species'] = species_code
            annotations['BirdVoxClassify Family'] = family_name
            annotations['BirdVoxClassify Order'] = order_name
            
            classification, _ = \
                _get_classification(species_code, family_name, order_name)
            if classification is not None:
                annotations['Classification'] = classification
            
            annotations['Detector Score'] = detector_score
            
            self._listener.process_clip(
                start_index, self._clip_length, annotations=annotations)


    def _process_checklist_file_2(self, reader):
        
        """Processes an eight-column BirdVoxDetect checklist file."""
        
        for row in reader:
            
            start_index = self._get_clip_start_index(row[0])
            detector_score = float(row[1])
            order_name = _get_order_name(row[2])
            order_score = float(row[3])
            family_name = row[4]
            family_score = float(row[5])
            species_code = row[6]
            species_score = float(row[7])
            
            annotations = {}
            
            # In the following, we use the term "Confidence" in the
            # annotation names since that is what BirdVoxDetect uses.
            # Vesper uses the term "Score" instead, for example in its
            # "Detector Score" and "Classification Score" annotation names.
            annotations['BirdVoxClassify Order'] = order_name
            annotations['BirdVoxClassify Order Confidence'] = order_score
            annotations['BirdVoxClassify Family'] = family_name
            annotations['BirdVoxClassify Family Confidence'] = family_score
            annotations['BirdVoxClassify Species'] = species_code
            annotations['BirdVoxClassify Species Confidence'] = species_score
            
            classification, classification_score = \
                _get_classification(
                    species_code, family_name, order_name,
                    species_score, family_score, order_score)
            if classification is not None:
                annotations['Classification'] = classification
                annotations['Classification Score'] = classification_score
            
            annotations['Detector Score'] = detector_score
            
            self._listener.process_clip(
                start_index, self._clip_length, annotations=annotations)


_ORDER_NAME_CORRECTIONS = {
    'Passeriforme': 'Passeriformes'
}


def _get_order_name(order_name):
    return _ORDER_NAME_CORRECTIONS.get(order_name, order_name)


_CLASSIFICATION_PREFIX = 'Call.'


def _get_classification(
        species_code, family_name, order_name,
        species_score=None, family_score=None, order_score=None):
    
    if species_code != 'OTHE':
        return _CLASSIFICATION_PREFIX + species_code, species_score
    elif family_name != 'other':
        return _CLASSIFICATION_PREFIX + family_name, family_score
    elif order_name != 'other':
        return _CLASSIFICATION_PREFIX + order_name, order_score
    else:
        return None, None


def _create_detector_class(detector_version, threshold_type, threshold):
    
    threshold_string = f'{threshold:02d}'
    
    class_name = f'Detector{threshold_type}{threshold_string}'
    
    extension_name = \
        f'BirdVoxDetect {detector_version} {threshold_type} {threshold_string}'
    
    settings = Settings(
        detector_version=detector_version,
        threshold=threshold)
     
    class_dict = {
        'extension_name': extension_name,
        '_settings': settings
    }
    
    cls = type(class_name, (_Detector,), class_dict)
    
    globals()[class_name] = cls


def _create_detector_classes():
    for detector_version in _DETECTOR_VERSIONS:
        for threshold_type in ('AT',):
            for threshold in [10, 20, 30, 40, 50, 60, 70, 80, 90]:
                _create_detector_class(
                    detector_version, threshold_type, threshold)


_create_detector_classes()


def _show_detector_classes():
    print('BirdVoxDetect detector classes:')
    items = sorted(globals().items(), key=lambda i: i[0])
    for key, value in items:
        if key.startswith('Detector') and key != 'DetectorError':
            extension_name = value.extension_name
            settings = value._settings.__dict__
            print(f"    {key} '{extension_name}' {settings}")


# _show_detector_classes()


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
