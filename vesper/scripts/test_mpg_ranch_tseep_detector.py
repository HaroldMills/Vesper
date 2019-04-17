"""
Script that runs MPG Ranch Tseep detector on one wave file.

The script takes a single command line argument, the path of the
wave file on which to run the detector.
"""


import sys

from vesper.mpg_ranch.nfc_detector_0_0.detector import TseepDetector
from vesper.signal.wave_audio_file import WaveAudioFileReader


READ_SIZE = 60


def main():
    
    file_path = sys.argv[1]
    
    reader = WaveAudioFileReader(file_path)
    sample_rate = reader.sample_rate
    length = reader.length
    
    listener = Listener(sample_rate)
    detector = TseepDetector(sample_rate, listener)
    
    max_read_size = int(round(READ_SIZE * sample_rate))
    
    start_index = 0
    
    while start_index != length:
        
        read_size = min(max_read_size, length - start_index)
        samples = reader.read(start_index, read_size)[0]
        
        # print(start_index, samples.shape)
        
        detector.detect(samples)
        
        start_index += read_size
        
    detector.complete_detection()
    
    
class Listener:
    
    
    def __init__(self, sample_rate):
        self._sample_rate = sample_rate
        
        
    def process_clip(self, start_index, length, threshold, annotations):
        start_time = start_index / self._sample_rate
        hours = int(start_time // 3600)
        minutes = int((start_time - hours * 3600) // 60)
        seconds = int(start_time % 60)
        duration = length / self._sample_rate
        print(
            'detected clip: {}:{:02d}:{:02d} {} {}'.format(
                hours, minutes, seconds, duration, annotations))


if __name__ == '__main__':
    main()
