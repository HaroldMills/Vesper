"""Clip bandwidth measurements."""


import numpy as np

import vesper.util.time_frequency_analysis_utils as tfa_utils


def equivalent_bandwidth(x):
    return np.sum(x) / np.max(x)


_SMALL_PROBABILITY = 1e-20


def entropy(x):
    p = x / np.sum(x)
    p[p == 0] = _SMALL_PROBABILITY
    return -np.sum(p * np.log(p))


def apply_measurement_to_spectra(
        measurement, spectrogram, start_freq=None, end_freq=None,
        denoise=False, block_size=1):
    
    """Applies a measurement to each spectrum of a spectrogram."""
    
    num_spectra = len(spectrogram.spectra)
    
    if num_spectra == 0:
        return np.array([])
    
    if start_freq is None:
        start_index = 0
    else:
        start_index = int(round(start_freq / spectrogram.freq_spacing))
        
    if end_freq is None:
        end_index = len(spectrogram.spectra[0])
    else:
        end_index = int(round(end_freq / spectrogram.freq_spacing)) + 1
        
    s = spectrogram.spectra[:, start_index:end_index]
#    s = spectrogram_utils.log_to_linear(s)
    s = np.power(10, s / 10.)
    
    if denoise:
        tfa_utils.denoise(s, out=s)
    
    num_blocks = num_spectra - block_size + 1
    measurements = np.array([_measure(measurement, s, i, block_size)
                            for i in range(num_blocks)])
    
    t = spectrogram.times
    times = np.array([np.mean(t[i:i + block_size])
                      for i in range(num_blocks)])
    
    return measurements, times


def _measure(measurement, s, i, block_size):
    block = s[i:i + block_size]
    return measurement(block.ravel())
