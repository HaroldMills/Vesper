"""Utility functions for time-frequency analysis."""


import math

import numpy as np


def get_num_analyses(num_samples, window_size, hop_size):
    if num_samples < window_size:
        return 0
    else:
        return int(math.floor(
            (num_samples - window_size) / float(hop_size) + 1))
        
        
def get_dft_analysis_data(sample_rate, dft_size, window_size):
    
    if dft_size is None:
        dft_size = get_dft_size(window_size)
        
    freqs = get_dft_freqs(sample_rate, dft_size)
    
    return (dft_size, freqs)
        
    
def get_dft_size(window_size):
    
    """
    Returns the smallest power of two that is at least the specified
    window size.
    """
    
    dft_size = 1
    while dft_size < window_size:
        dft_size <<= 1
            
    return dft_size


def get_dft_freqs(sample_rate, dft_size):
    
    """
    Gets the frequencies of a DFT analysis.
    
    It is assumed that the analyzed signal is real, so that the
    analysis will be performed at `dft_size / 2 + 1` frequencies.
    """
    
    num_freqs = dft_size / 2 + 1
    spacing = sample_rate / (dft_size - 1.)
    return np.arange(num_freqs) * spacing


def compute_stft(samples, window, hop_size, dft_size):
    
    """Computes the short-time Fourier transform (STFT) of a signal."""
    
    window_size = len(window)
    num_spectra = get_num_analyses(
        len(samples), window_size, hop_size)
    
    j = 0
    x = np.zeros(dft_size, dtype='float32')
    stft = np.zeros((num_spectra, dft_size / 2 + 1), dtype='complex64')
    
    for i in range(num_spectra):
        x[:window_size] = samples[j:(j + window_size)] * window
        stft[i, :] = np.fft.rfft(x)
        j += hop_size
        
    return stft


def compute_spectrogram(samples, window, hop_size, dft_size):
    
    """
    Computes the spectrogram of a signal.
    
    The spectrogram is the squared magnitude of the short-time Fourier
    transform. See also the function `_compute_stft`.
    """
    
    window_size = len(window)
    num_spectra = get_num_analyses(
        len(samples), window_size, hop_size)
    
    j = 0
    x = np.zeros(dft_size, dtype='float32')
    spectrogram = np.zeros((num_spectra, dft_size / 2 + 1), dtype='float32')
    
    for i in range(num_spectra):
        x[:window_size] = samples[j:(j + window_size)] * window
        dft = np.fft.rfft(x)
        spectrogram[i, :] = (dft * dft.conj()).real
        j += hop_size
        
    return spectrogram
        
    
def adjust_spectrogram_powers(spectrogram, dft_size):
    
    """
    Adjusts spectrogram powers.
    
    This function scales a spectrogram so that if it was computed with
    a rectangular window, the sum of the bins of each spectrum of the
    spectrogram equals the norm squared of the sample vector from which
    it was computed.
    """
         
    # We scale the entire spectrum by `1. / dft_size`, and scale
    # all but the first and last bins by an additional factor
    # of two. The latter scaling is to include energy from the
    # negative frequency bins (the first and last bins, whose
    # center frequencies are zero and half the sample rate, have
    # no corresponding negative frequency bins). For efficiency
    # reasons, we perform these scalings first by scaling all
    # bins by `2. / dft_size`, and subsequently scaling the
    # first and last bins by one half.
    
    spectrogram *= 2. / dft_size
    spectrogram[:, 0] *= .5
    spectrogram[:, -1] *= .5


# It's important not to make this too small, so that it is representable
# as a 32-bit floating point number. The smallest normal (i.e. not
# denormalized) positive floating point number is about 1.18e-38.
_SMALL_POWER = 1e-30


def linear_to_log(spectra, ref_power=1., out=None):
    
    """Converts linear spectral values to logarithmic ones."""
    
    if out is None:
        out = np.array(spectra)
        
    elif out is not spectra:
        np.copyto(out, spectra)

    if ref_power != 1:
        out /= ref_power
        
    # We substitute `_SMALL_POWER` for small values in the spectra
    # before taking logs to avoid divide by zero error messages
    # in the call to `np.log10`, and to avoid minus infinity
    # values in the output. Having large negative numbers is
    # preferable to having infinities since the latter do not
    # play well with other numbers in subsequent arithmetic
    # (for example 0 times infinity is `NaN`).
    out[out < _SMALL_POWER] = _SMALL_POWER
    
    np.log10(out, out=out)
    
    out *= 10
    
    return out


def log_to_linear(spectra, ref_power=1., out=None):
    
    """Converts logarithmic spectral values to linear ones."""
    
    if out is None:
        out = np.array(spectra)
        
    elif out is not spectra:
        np.copyto(out, spectra)
        
    out /= 10
    
    if ref_power != 1:
        out += np.log10(ref_power)
        
    np.power(10, out, out=out)
    
    return out


# TODO: Revisit this function, and consider renaming and/or reimplementing
# it. The current implementation clips spectral values below according to
# order statistical thresholds. We use the function to reduce the variation
# within spectra that contain only background noise. This isn't what is
# usually meant by the term "denoising", however, which usually implies
# *zeroing* bins that are deemed to contain only background noise.
def denoise(spectra, percentile=50, out=None):
    
    """Denoises a sequence of spectra."""
    
    if out is None:
        out = np.array(spectra)
        
    elif out is not spectra:
        np.copyto(out, spectra)
        
    # Compute percentile spectral values across time for each frequency bin.
    percentiles = np.percentile(out, percentile, axis=0)
    
    # The `np.percentile` function yields an array whose dtype is float64,
    # even though `out` has dtype float32. We create an array with dtype
    # float32 to avoid implicit casting errors in subsequent arithmetic.
    percentiles = np.array(percentiles, dtype='float32')
    
    # Subtract percentiles from spectral values.
    out -= percentiles
    
    # Zero negative spectral values.
    out[out < 0.] = 0.
    
    # Add percentiles back.
    out += percentiles
    
    return out
