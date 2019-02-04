"""Module containing `WaveFileReader` class."""


import wave

import numpy as np


class WaveFileReader:
    
    """Simple reader for 16-bit, uncompressed wave files."""
    
    
    def __init__(self, file_path):
        self._reader = wave.open(file_path, 'rb')
        (self.num_channels, _, self.sample_rate, self.length, _, _) = \
            self._reader.getparams()

        
    def read(self, start_index, length):
        self._reader.setpos(start_index)
        buffer = self._reader.readframes(length)
        samples = np.frombuffer(buffer, dtype='<i2')
        samples = samples.reshape((length, self.num_channels)).transpose()
        return samples


    def close(self):
        self._reader.close()
