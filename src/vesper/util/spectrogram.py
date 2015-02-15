"""Module containing `Spectrogram` class."""


from __future__ import print_function

import math

from scipy import interpolate
import numpy as np


# TODO: Compare this spectrogram carefully to that computed by the
# Matplotlib `specgram` function, in terms of both functionality
# and efficiency.


class Spectrogram(object):
     
     
    # TODO: Have a separate method parameter for each spectrogram parameter?
    # TODO: Make `spectra` a property and compute spectra lazily?
    def __init__(self, sound, params):
         
        """
        Initializes this spectrogram.
         
        :Parameters:
         
            sound : `object`
                the sound of which to compute the spectrogram.
                 
                This parameter must be a Python object with the
                following attributes:
                 
                    samples : NumPy array
                        the samples of the sound
                         
                    sample_rate : `float`
                        the sample rate of the sound in hertz.
             
            params : `object`
                the spectrogram parameters.
             
                This parameter must be a Python object with the
                followingattributes:
             
                    window : NumPy array
                        the data window to use for the spectrogram.
                 
                        The data window may be of any length.
                 
                    hop_size : `int`
                        the spectrogram hop size in samples.
                         
                    dft_size : `int`
                        the DFT size for the spectrogram, in samples,
                        or `None`.
                         
                        The DFT size must be either a power of two
                        or `None`. If `None`, the DFT size is taken to
                        be the smallest power of two that is at least
                        the window size.
                         
                    ref_power : `float`
                        the reference power for the spectrogram, or `None`.
                         
                        If the reference power is not `None`, the
                        units of the returned spectrogram magnitude
                        are decibels with respect to the reference
                        power. If the reference power is `None`, no
                        logarithms are taken.
        """
     
     
        self.sound = sound
         
        (self.window, self.hop_size, self.dft_size, self.ref_power) = \
            (params.window, params.hop_size, _get_dft_size(params),
             params.ref_power)
             
        spectra = _compute_spectrogram(
            self.sound.samples, self.window, self.hop_size, self.dft_size)
        
        _adjust_spectrogram_powers(spectra, self.dft_size)
        
        if self.ref_power is not None:
            linear_to_log(spectra, self.ref_power, spectra)
                     
        sample_rate = float(sound.sample_rate)
        self.frame_rate = sample_rate / self.hop_size
        self.max_freq = sample_rate / 2
         
        (self.num_spectra, self.num_bins) = spectra.shape
        self.spectra = spectra
        self._spectrum_times = None
        self._bin_freqs = None
        self._min_value = None
        self._max_value = None
         
        self._interpolator = None
         
         
    @property
    def spectrum_times(self):
         
        if self._spectrum_times is None:
            offset = self.window.size / 2. / self.sound.sample_rate
            self._spectrum_times = \
                offset + np.arange(self.num_spectra) / self.frame_rate
             
        return self._spectrum_times
     
     
    @property
    def bin_size(self):
        return self.max_freq / (self.num_bins - 1)
     
     
    @property
    def bin_freqs(self):
        if self._bin_freqs is None:
            self._bin_freqs = np.arange(self.num_bins) * self.bin_size
        return self._bin_freqs
             
             
    @property
    def min_value(self):
        if self._min_value is None and self.num_spectra != 0:
            self._min_value = np.min(np.min(self.spectra))
        return self._min_value
     
     
    @property
    def max_value(self):
        if self._max_value is None and self.num_spectra != 0:
            self._max_value = np.max(np.max(self.spectra))
        return self._max_value
     
     
    def interpolate(self, times, freqs):
         
        if self._interpolator is None:
            self._interpolator = interpolate.RectBivariateSpline(
                self.spectrum_times, self.bin_freqs, self.spectra, kx=1, ky=1)
             
        return self._interpolator(times, freqs)
        
        
def _get_dft_size(params):
    
    dft_size = params.dft_size
    
    if dft_size is None:
        
        # Find the smallest power of two that is at least `params.window.size`.
        dft_size = 1
        while dft_size < params.window.size:
            dft_size <<= 1
            
    return dft_size


def _compute_stft(samples, window, hop_size, dft_size):
    
    """Computes the short-time Fourier transform (STFT) of a signal."""
    
    num_spectra, window_size, window_samples, dft_size = \
        _get_stft_data(samples, window, hop_size, dft_size)
        
    j = 0
    x = np.zeros(dft_size, dtype='float32')
    stft = np.zeros((num_spectra, dft_size / 2 + 1), dtype='complex64')
    
    for i in xrange(num_spectra):
        x[:window_size] = samples[j:(j + window_size)] * window_samples
        stft[i, :] = np.fft.rfft(x)
        j += hop_size
        
    return stft


def _get_stft_data(samples, window, hop_size, dft_size):

    num_samples = len(samples)
    window_size = window.size
    window_samples = window.samples
    
    if num_samples < window_size:
        num_spectra = 0
    else:
        num_spectra = int(math.floor(
            (num_samples - window_size) / float(hop_size)) + 1)
        
    return (num_spectra, window_size, window_samples, dft_size)
        

def _compute_spectrogram(samples, window, hop_size, dft_size):
    
    """
    Computes the spectrogram of a signal.
    
    The spectrogram is the squared magnitude of the short-time Fourier
    transform. See also the function `_compute_stft`.
    """
    
    num_spectra, window_size, window_samples, dft_size = \
        _get_stft_data(samples, window, hop_size, dft_size)
        
    j = 0
    x = np.zeros(dft_size, dtype='float32')
    spectrogram = np.zeros((num_spectra, dft_size / 2 + 1), dtype='float32')
    
    for i in xrange(num_spectra):
        x[:window_size] = samples[j:(j + window_size)] * window_samples
        dft = np.fft.rfft(x)
        spectrogram[i, :] = (dft * dft.conj()).real
        j += hop_size
        
    return spectrogram
        
    
def _adjust_spectrogram_powers(spectrogram, dft_size):
    
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
