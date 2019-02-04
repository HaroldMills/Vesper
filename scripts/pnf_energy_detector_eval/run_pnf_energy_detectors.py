"""
Runs detectors on the BirdVox-full-night recordings.

This script runs one or more detectors on a set of BirdVox-full-night
recordings. It writes metadata for the resulting detections to an output
CSV file for further processing, for example for plotting precision vs.
recall curves.

The inputs required by this script are:

1. The BirdVox-full-night recordings, as WAV files. The BirdVox-full-night
dataset includes the recordings as FLAC files: you can use Sox
(http://sox.sourceforge.net/) or some other software to convert the FLAC
files to WAV files. The directory containing the WAV files is specified
by scripts.pnf_energy_detector_eval.utils.RECORDINGS_DIR_PATH.

The outputs produced by this script are:

1. A CSV file, named either "Tseep.csv" or "Thrush.csv", depending on the
value of the DETECTOR_TYPE module attribute. Each line of the file contains
data describing one clip produced by a detector. The directory of the file
is specified by scripts.pnf_energy_detector_eval.utils.WORKING_DIR_PATH.
"""


from multiprocessing import Pool
import csv
import math
import time

from vesper.pnf.pnf_2018_baseline_detector_1_0 import BaselineDetector
from vesper.pnf.pnf_energy_detector_1_0 import Detector
from vesper.util.bunch import Bunch
from scripts.pnf_energy_detector_eval.wave_file_reader import WaveFileReader
import scripts.pnf_energy_detector_eval.utils as utils


DETECTOR_TYPE = 'Tseep'
"""The type of detector to run, either `'Tseep'` or `'Thrush'`."""


PARAMETER_NAME = 'window_type'
"""Variable parameter name."""


PARAMETER_VALUES = ['hann']
"""Parameter values for which to run detectors."""
    

DETECTOR_BASE_SETTINGS = {
    
    'Tseep': Bunch(
        window_type='hann',
        window_size=.005,                           # seconds
        hop_size=50,                                # percent
        start_frequency=5000,                       # hertz
        end_frequency=10000,                        # hertz
        power_filter_passband_end_frequency=5,      # hertz
        power_filter_stopband_start_frequency=15,   # hertz
        power_filter_length=31,                     # samples
        delay=.050,                                 # seconds
        thresholds=[2.7],                           # dimensionless
        initial_clip_padding=.050,                  # seconds
        clip_duration=.300                          # seconds
    ),
    
    'Thrush': Bunch(
        window_type='hann',
        window_size=.005,                           # seconds
        hop_size=50,                                # percent
        start_frequency=2600,                       # hertz
        end_frequency=5000,                         # hertz
        power_filter_passband_end_frequency=5,      # hertz
        power_filter_stopband_start_frequency=15,   # hertz
        power_filter_length=31,                     # samples
        delay=.080,                                 # seconds
        thresholds=[2.5],                           # dimensionless
        initial_clip_padding=.050,                  # seconds
        clip_duration=.400                          # seconds
    )
    
}
"""Base settings for detector variants."""


INCLUDE_BASELINE_DETECTOR = True
"""
True if and only if baseline detector should be run in addition to
detectors specified by `PARAMETER_NAME` and `PARAMETER_VALUES`.
"""


BASELINE_DETECTOR_SETTINGS = {
    
    'Tseep': Bunch(
        window_type='hann',
        window_size=.005,                 # seconds
        hop_size=50,                      # percent
        start_frequency=6000,             # hertz
        end_frequency=10000,              # hertz
        integration_time=.090,            # seconds
        delay=.020,                       # seconds
        thresholds=[2],                   # dimensionless
        min_transient_duration=.100,      # seconds
        max_transient_duration=.400,      # seconds
        initial_clip_padding=.050,        # seconds
        clip_duration=.300                # seconds
    ),

    'Thrush': Bunch(
        window_type='hann',
        window_size=.005,                 # seconds
        hop_size=50,                      # percent
        start_frequency=2800,             # hertz
        end_frequency=5000,               # hertz
        integration_time=.180,            # seconds
        delay=.020,                       # seconds
        thresholds=[1.3],                 # dimensionless
        min_transient_duration=.100,      # seconds
        max_transient_duration=.400,      # seconds
        initial_clip_padding=.050,        # seconds
        clip_duration=.400                # seconds
    )
    
}
"""Baseline detector settings."""


THRESHOLDS = utils.get_detection_thresholds()
"""Detection thresholds at which to run detectors."""


UNIT_NUMS = utils.UNIT_NUMS
"""Units for which to run detectors."""


NUM_WORKER_PROCESSES = 3
"""
Number of worker processes in process pool.

This is the maximum number of detectors that will run simultaneously.
"""

CHUNK_SIZE = 100000
"""
Wave file read chunk size in samples.

Detectors run fastest for intermediate chunk sizes, depending on aspects
of the particular computer on which they are run. I suspect, for example,
the processor core memory cache size influences the range of good chunk
sizes. For sufficiently small chunk sizes processing loop overhead becomes
large enough to harm performance, while for larger chunk sizes memory cache
misses become a problem.
"""


def main():
    
    detector_settings = create_detector_settings()
    
    args = [(detector_settings, i) for i in UNIT_NUMS]
    
    with Pool(NUM_WORKER_PROCESSES) as pool:
        results = pool.starmap(run_detectors_on_one_recording, args)
        
    results = sorted(results)
    
    write_clips_file(results)
    
    utils.announce('Harold, your detection script has finished.')
    
    
def create_detector_settings():
    return dict([
        create_detector_settings_aux(DETECTOR_TYPE, PARAMETER_NAME, value)
        for value in PARAMETER_VALUES])


def create_detector_settings_aux(
        detector_type, parameter_name, parameter_value):
    
    value_string = format_parameter_value(parameter_value)
    name = '{} {}'.format(detector_type, value_string)
    
    base_settings = DETECTOR_BASE_SETTINGS[detector_type]
        
    kwargs = {
        parameter_name: parameter_value,
    }
    
    settings = Bunch(base_settings, **kwargs)
    
    return name, settings


def format_parameter_value(value):
    return str(value)


def run_detectors_on_one_recording(detector_settings, unit_num):
        
    file_path = utils.get_recording_file_path(unit_num)
        
    print('Running detectors for unit {} on file "{}"...'.format(
        unit_num, file_path))
    
    start_time = time.time()
    
    reader = WaveFileReader(str(file_path))
    num_chunks = int(math.ceil(reader.length / CHUNK_SIZE))
    sample_rate = reader.sample_rate
    
    detectors, listeners = create_detectors(
        detector_settings, sample_rate, unit_num)
        
    for i, samples in enumerate(generate_sample_buffers(reader)):
        if i != 0 and i % 1000 == 0:
            print('    Unit {} chunk {} of {}...'.format(
                unit_num, i, num_chunks))
        for detector in detectors:
            detector.detect(samples[0])
                       
    for detector in detectors:
        detector.complete_detection()

    reader.close()
    
    processing_time = time.time() - start_time
    file_duration = reader.length / sample_rate
    show_processing_time(processing_time, unit_num, file_duration)
    
    return unit_num, listeners
        

def create_detectors(detector_settings, sample_rate, unit_num):
    
    if INCLUDE_BASELINE_DETECTOR:
        pairs = [create_baseline_detector(sample_rate, unit_num)]
    else:
        pairs = []
        
    detector_names = sorted(detector_settings.keys())
    
    pairs += [
        create_detector(
            detector_name, detector_settings, sample_rate, unit_num)
        for detector_name in detector_names]

    return zip(*pairs)


def create_baseline_detector(sample_rate, unit_num):
    
    settings = BASELINE_DETECTOR_SETTINGS[DETECTOR_TYPE]
    settings.thresholds = THRESHOLDS
    
    detector_name = 'Baseline {}'.format(DETECTOR_TYPE)
    listener = Listener(detector_name, unit_num)
    
    detector = BaselineDetector(settings, sample_rate, listener)
        
    return detector, listener
             

def create_detector(detector_name, detector_settings, sample_rate, unit_num):
    
    settings = detector_settings[detector_name]
    settings.thresholds = THRESHOLDS
    
    listener = Listener(detector_name, unit_num)
    
    detector = Detector(settings, sample_rate, listener)
        
    return detector, listener


def generate_sample_buffers(file_reader):
    start_index = 0
    while start_index < file_reader.length:
        length = min(CHUNK_SIZE, file_reader.length - start_index)
        yield file_reader.read(start_index, length)
        start_index += CHUNK_SIZE


def show_processing_time(processing_time, unit_num, file_duration):
    factor = file_duration / processing_time
    print(
        ('Ran detectors for unit {} on {}-second file in {} seconds, {} '
         'times faster than real time.').format(
             unit_num, round_(file_duration), round_(processing_time),
             round_(factor)))
        
        
def round_(t):
    return round(10 * t) / 10


def write_clips_file(results):
    
    file_path = utils.get_clips_file_path(DETECTOR_TYPE)
    
    with open(file_path, 'w') as file_:
        
        writer = csv.writer(file_)
        
        writer.writerow(
            ['Detector', 'Unit', 'Threshold', 'Start Index', 'Length'])
        
        for unit_num, listeners in results:
            
            for listener in listeners:
                
                print('For unit {}, {} detector produced {} clips.'.format(
                    unit_num, listener.detector_name, len(listener.clips)))
                
                listener.clips.sort()
                
                writer.writerows(listener.clips)
                

class Listener:
    
    
    def __init__(self, detector_name, unit_num):
        self.detector_name = detector_name
        self.unit_num = unit_num
        self.clips = []
        
        
    def process_clip(self, start_index, length, threshold):
        self.clips.append([
            self.detector_name, self.unit_num, threshold, start_index, length])
        
        
if __name__ == '__main__':
    main()
