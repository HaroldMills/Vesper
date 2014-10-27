"""Utility functions pertaining to sounds."""


from PyQt4.QtGui import QSound
import numpy as np

from nfc.util.bunch import Bunch
import nfc.util.audio_file_utils as audio_file_utils


def read_sound_file(path):
    (samples, sample_rate) = audio_file_utils.read_wave_file(path)
    samples = samples[0]
    return Bunch(samples=samples, sample_rate=sample_rate)
    


def write_sound_file(path, sound):
    samples = np.array([sound.samples])
    audio_file_utils.write_wave_file(path, samples, sound.sample_rate)
    
    
def play_sound_file(path):
    QSound.play(path)
