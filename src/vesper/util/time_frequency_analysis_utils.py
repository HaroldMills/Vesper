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
    
    for i in xrange(num_spectra):
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
    
    for i in xrange(num_spectra):
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
    
    # TODO: If the following is unacceptably slow, implement a fast
    # replacement, for example using Cython or a NumPy ufunc.
        
    if out is None:
        spectra = np.array(spectra)

    if ref_power != 1:
        spectra /= ref_power
        
    # We substitute `_SMALL_POWER` for small values in the spectra
    # before taking logs to avoid divide by zero error messages
    # in the call to `np.log10`, and to avoid minus infinity
    # values in the output. Having large negative numbers is
    # preferable to having infinities since the latter do not
    # play well with other numbers in subsequent arithmetic
    # (for example 0 times infinity is `NaN`).
    spectra[spectra < _SMALL_POWER] = _SMALL_POWER
    
    np.log10(spectra, out=spectra)
    
    spectra *= 10
    
    return spectra


def log_to_linear(spectra, ref_power=1., out=None):
    
    """Converts logarithmic spectral values to linear ones."""
    
    if out is None:
        spectra = np.array(spectra)
        
    spectra /= 10
    
    if ref_power != 1:
        spectra += np.log10(ref_power)
        
    np.power(10, spectra, spectra)
    
    return spectra


def denoise(spectra, out=None):
    
    """
    Denoises a sequence of spectra.
    
    The spectrum powers are assumed to be linear, not logarithmic.
    """
    
    if out is None:
        spectra = np.array(spectra)
        
    # Transpose so first dimension is frequency rather than time.
    s = spectra.transpose()
    
    # Compute median spectral values across time for each frequency bin.
    m = np.median(s)
    
    # Zero spectral values that don't exceed the medians.
    s[s <= m] = 0

    # Transpose back so first dimension is again time.
    return s.transpose()
