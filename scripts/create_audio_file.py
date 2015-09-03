"""Creates a simple test audio file in the current directory."""


import numpy as np

import vesper.util.audio_file_utils as audio_file_utils


_LENGTH = 10
_NUM_CHANNELS = 2
_SAMPLE_RATE = 24000


def _main():
    samples = np.arange(_LENGTH)
    samples = np.vstack(samples + i * 1000 for i in range(_NUM_CHANNELS))
    audio_file_utils.write_wave_file('test.wav', samples, _SAMPLE_RATE)
    
    
if __name__ == '__main__':
    _main()
    