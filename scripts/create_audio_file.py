"""Creates a simple test audio file in the current directory."""


import numpy as np

import vesper.util.audio_file_utils as audio_file_utils


START = 0
LENGTH = 10
NUM_CHANNELS = 2
SAMPLE_RATE = 24000
FILE_NAME = 'test.wav'


def main():
    samples = np.arange(START, START + LENGTH)
    channels = list(samples + i * 1000 for i in range(NUM_CHANNELS))
    samples = np.vstack(channels)
    audio_file_utils.write_wave_file(FILE_NAME, samples, SAMPLE_RATE)
    
    
if __name__ == '__main__':
    main()
