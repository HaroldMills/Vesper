"""
PySoundFile SoundFile substitute that supports only single-channel,
16-bit wave files.

The PySoundFile library wraps the libsndfile library as a Python package.
PySoundFile includes a SoundFile class that birdvoxdetect uses to read
data from single-channel sound files. I have run into several problems
using PySoundFile with Vesper, both because I can't seem to build a
Vesper Conda package that depends on PySoundFile and because I can't
seem to install PySoundFile on Windows using Conda. Until these problems
are resolved, I have chosen not to use PySoundFile in Vesper, and to
use the SoundFile class defined in this module in its place for
birdvoxdetect. The SoundFile class is a drop-in substitute for
PySoundFile's SoundFile class (at least as far as birdvoxdetect is
concerned), except that it supports only single-channel, 16-bit wave
files rather than audio files of many different formats.
"""


import wave

import numpy as np


_WAVE_SAMPLE_DTYPE = np.dtype('<i2')


class SoundFile:
    
    
    def __init__(self, file_path):
        self._reader = wave.open(file_path, 'rb')
            
    
    @property
    def samplerate(self):
        return self._reader.getframerate()
    
    
    @property
    def channels(self):
        return self._reader.getnchannels()
    
    
    def __len__(self):
        return self._reader.getnframes()
    
    
    def seek(self, position):
        self._reader.setpos(position)
    
    
    def read(self, num_samples):
        data = self._reader.readframes(num_samples)
        samples = np.frombuffer(data, dtype=_WAVE_SAMPLE_DTYPE)
        return samples / 32768.
