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
by scripts.detector_eval.utils.RECORDINGS_DIR_PATH.

The outputs produced by this script are:

1. The file "Clips.csv", containing the results of detector runs. Each
line of this file contains data describing one clip produced by a detector.
The directory of the file is specified by
scripts.detector_eval.utils.WORKING_DIR_PATH.
"""


from multiprocessing import Pool
import csv
import math
import time

from vesper.pnf.pnf_2017_basic_detector_1_0_alpha_1 import Detector
from vesper.util.bunch import Bunch
from scripts.detector_eval.wave_file_reader import WaveFileReader
import scripts.detector_eval.utils as utils


DETECTOR_TYPE = 'Tseep'
"""The type of detector to run, either `'Tseep'` or `'Thrush'`."""


# DETECTOR_VARIANTS = [
#     (50, 100),
#     (50, 200),
#     (100, 200)
# ]
DETECTOR_VARIANTS = [
    (20, 40),
    (25, 50),
    (30, 60),
    (35, 70),
    (40, 80),
    (45, 90),
    (50, 100),
]
"""Pairs of (integration_time, delay) settings for which to run detectors."""
    

INCLUDE_OLD_BIRD_DETECTOR = True
"""
True if and only if Old Bird detector should be run in addition to
detectors specified by `DETECTOR_SETTINGS`.
"""


THRESHOLDS = utils.get_detection_thresholds()
"""Detection thresholds at which to run detectors."""


TSEEP_SETTINGS = Bunch(
    start_frequency=6000,             # hertz
    end_frequency=10000,              # hertz
    window_size=.005,                 # seconds
    hop_size=.0025,                   # seconds
    integration_time=.090,            # seconds
    delay=.020,                       # seconds
    thresholds=THRESHOLDS,            # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.2,          # seconds
    clip_duration=.6                  # seconds
)
"""Settings for a detector very similar to the Old Bird Tseep detector."""


THRUSH_SETTINGS = Bunch(
    start_frequency=2800,             # hertz
    end_frequency=5000,               # hertz
    window_size=.005,                 # seconds
    hop_size=.0025,                   # seconds
    integration_time=.180,            # seconds
    delay=.020,                       # seconds
    thresholds=THRESHOLDS,            # dimensionless
    min_transient_duration=.100,      # seconds
    max_transient_duration=.400,      # seconds
    initial_clip_padding=.2,          # seconds
    clip_duration=.6                  # seconds
)
"""Settings for a detector very similar to the Old Bird Thrush detector."""


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
    
    
def create_detector_settings():
    
    base_settings = \
        TSEEP_SETTINGS if DETECTOR_TYPE == 'Tseep' else THRUSH_SETTINGS
        
    # Create settings for range of integration times.
    settings = dict([
        create_detector_settings_aux(DETECTOR_TYPE, base_settings, *pair)
        for pair in DETECTOR_VARIANTS])
    
    if INCLUDE_OLD_BIRD_DETECTOR:
        
        # Create Old Bird settings.
        name = 'Old Bird {}'.format(DETECTOR_TYPE)
        settings[name] = base_settings
             
    return settings


def create_detector_settings_aux(
        detector_type, base_settings, integration_time, delay):
    
    name = '{} {:03} {:03}'.format(detector_type, integration_time, delay)
    
    integration_time /= 1000
    delay /= 1000
    
    settings = Bunch(
        base_settings,
        integration_time=integration_time,
        delay=delay,
        initial_clip_padding=.2,
        clip_duration=.6)
    
    return name, settings


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
    detector_names = sorted(detector_settings.keys())
    pairs = [
        create_detector(
            detector_settings, detector_name, sample_rate, unit_num)
        for detector_name in detector_names]
    return zip(*pairs)


def create_detector(detector_settings, detector_name, sample_rate, unit_num):
    settings = detector_settings[detector_name]
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
    
    file_path = utils.get_clips_file_path()
    
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
