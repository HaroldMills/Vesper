"""Module containing `RatioFileWriter` class."""


import wave

import numpy as np


_FILE_PATH_FORMAT = '/Users/harold/Desktop/{} Ratios.wav'
_COUNT_LIMIT = 10


class RatioFileWriter:
    
    """
    Writes a .wav file containing detector audio input in one
    channel and inband power ratios in another.
    """
    
    def __init__(self, sample_rate, decimation_factor, detector_name):
        file_path = _FILE_PATH_FORMAT.format(detector_name)
        self._writer = wave.open(file_path, 'wb')
        self._writer.setparams((2, 2, sample_rate, 0, 'NONE', None))
        self._decimation_factor = decimation_factor
        self._count = 0
        
        
    def write(self, samples, ratios):
        
        if self._count != _COUNT_LIMIT:
            
            samples = np.array(np.round(samples), dtype='<i2')
            
            ratios = np.array(np.round(1000 * ratios), dtype='<i2')
            ratios = self._repeat_samples(ratios)
            
            if len(ratios) < len(samples):
                zeros = np.zeros(len(samples) - len(ratios), dtype='<i2')
                ratios = np.concatenate((zeros, ratios))
            
            data = np.zeros((2, len(samples)), dtype='<i2')
            data[0] = samples
            data[1] = ratios
            
            data = data.transpose().tostring()
            self._writer.writeframes(data)
            
            self._count += 1
            if self._count == _COUNT_LIMIT:
                self.close()
        
        
    def _repeat_samples(self, x):
        x.shape = (len(x), 1)
        y = np.ones((1, self._decimation_factor))
        z = x * y
        return z.flatten()
        
        
    def close(self):
        self._writer.close()
