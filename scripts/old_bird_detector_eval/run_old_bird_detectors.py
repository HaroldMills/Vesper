"""
Runs the Old Bird detectors on the BirdVox-full-night recordings.

This script runs the Old Bird Tseep and Thrush detectors on all of the
BirdVox-full-night recordings with multiple detection thresholds. It
writes metadata for the resulting detections to an output CSV file for
further processing, for example for plotting precision vs. recall curves.
"""


import csv
import time

import matplotlib.pyplot as plt
import numpy as np

from vesper.old_bird.old_bird_detector_redux_1_1_mt import (
    ThrushDetector, TseepDetector)
from vesper.signal.wave_audio_file import WaveAudioFileReader

import scripts.old_bird_detector_eval.utils as utils


QUICK_RUN = False

DETECTOR_CLASSES = {
    'Thrush': ThrushDetector,
    'Tseep': TseepDetector
}


class Listener:
    
    
    def __init__(self, name):
        self.name = name
        self.unit_num = None
        self.clips = []
        
        
    def process_clip(self, start_index, length, threshold):
        self.clips.append(
            [self.name, self.unit_num, threshold, start_index, length])
        
        
def main():
    
#     thresholds = get_detection_thresholds(utils.DETECTION_THRESHOLDS_POWER)
#     for i, t in enumerate(thresholds):
#         print(i, t)
#     return

#     plot_detection_thresholds()
#     return

    listeners = create_listeners()
    
    recordings_dir_path = utils.BIRDVOX_70K_ARCHIVE_RECORDINGS_DIR_PATH
    recording_file_paths = sorted(recordings_dir_path.iterdir())
        
    for file_path in recording_file_paths:
        
        if not file_path.name.endswith('.wav'):
            continue
        
        else:
            run_detectors_on_file(file_path, listeners)
            
        if QUICK_RUN:
            break
            
    write_detections_file(listeners)
    
    
def create_listeners():
    names = sorted(DETECTOR_CLASSES.keys())
    return [Listener(name) for name in names]
    
    
def run_detectors_on_file(file_path, listeners):
        
    print('Running detectors on file "{}"...'.format(file_path))
    
    unit_num = get_unit_num(file_path)
    
    for listener in listeners:
        listener.unit_num = unit_num
    
    start_time = time.time()
    
    reader = WaveAudioFileReader(str(file_path))
            
    sample_rate = reader.sample_rate
    
    detectors = [create_detector(sample_rate, l) for l in listeners]
        
    for i, samples in enumerate(generate_sample_buffers(reader)):
        if i != 0 and i % 100 == 0:
            print('    Chunk {}...'.format(i))
        for detector in detectors:
            detector.detect(samples[0])
                       
    for detector in detectors:
        detector.complete_detection()

    reader.close()
    
    processing_time = time.time() - start_time
    file_duration = reader.length / sample_rate
    show_processing_time(processing_time, file_duration)
        

def get_unit_num(file_path):
    return int(file_path.name.split()[1][:2])
    
    
def create_detector(sample_rate, listener):
    cls = DETECTOR_CLASSES[listener.name]
    thresholds = get_detection_thresholds(utils.DETECTION_THRESHOLDS_POWER)
    return cls(thresholds, sample_rate, listener)


def get_detection_thresholds(p):
    
    min_t = utils.MIN_DETECTION_THRESHOLD
    max_t = utils.MAX_DETECTION_THRESHOLD
    n = utils.NUM_DETECTION_THRESHOLDS
    y = (np.arange(n) / (n - 1)) ** p
    t = min_t + (max_t - min_t) * y
    t = list(t)
    t.append(1.3)   # Old Bird Thrush threshold
    t.append(2)     # Old Bird Tseep threshold
    t.sort()
    return t


def generate_sample_buffers(file_reader):
    
    chunk_size = 1000000
    
    start_index = 0
    
    while start_index < file_reader.length:
        length = min(chunk_size, file_reader.length - start_index)
        yield file_reader.read(start_index, length)
        start_index += chunk_size


def show_processing_time(processing_time, file_duration):
    factor = file_duration / processing_time
    print(
        ('Ran detectors on {}-second file in {} seconds, {} times faster '
         'than real time.').format(
             round_(file_duration), round_(processing_time), round_(factor)))
        
        
def round_(t):
    return round(10 * t) / 10


def write_detections_file(listeners):
    
    with open(utils.OLD_BIRD_CLIPS_FILE_PATH, 'w') as file_:
        
        writer = csv.writer(file_)
        
        writer.writerow(
            ['Detector', 'Unit', 'Threshold', 'Start Index', 'Length'])
        
        for listener in listeners:
            
            print('{} listener got {} clips.'.format(
                listener.name, len(listener.clips)))
            
            listener.clips.sort()
            
            writer.writerows(listener.clips)
    
    
def plot_detection_thresholds():
    
    _, axes = plt.subplots(figsize=(6, 6))
    
    t = get_exponential_detection_thresholds()
    axes.plot(t, marker='o', label='Exponential')
    
    for p in [2, 3, 4]:
        t = get_detection_thresholds(p)
        axes.plot(t, marker='o', label='Power {}'.format(p))
    
    axes.legend()
    plt.xlabel('Index')
    plt.ylabel('Threshold')
    plt.title('Detection Thresholds')
    plt.show()
    
    
def get_exponential_detection_thresholds():
     
    """
    Creates n thresholds ranging from a little more than 1 to m, with
    spacing between consecutive thresholds increasing exponentially.
    """
 
    m = utils.MAX_DETECTION_THRESHOLD
    n = utils.NUM_DETECTION_THRESHOLDS
    y = np.exp(np.log(m) / n)
    return y ** np.arange(1, n + 1)


if __name__ == '__main__':
    main()
