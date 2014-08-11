"""Module containing `Spectrogram` class."""


from __future__ import print_function

import math

from scipy import interpolate
import numpy as np


# It's important not to make this too small, so that it is representable
# as a 32-bit floating point number. The smallest normal (i.e. not
# denormalized) positive floating point number is about 1.18e-38.
_SMALL_POWER = 1e-30


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
    
    
        # The spectrogram is by definition the magnitude squared of the
        # Short-time Fourier Transform (STFT). See notes below about
        # how we scale the spectrogram so that for a rectangular window
        # the sum of the bins of each spectrum of the spectrogram equals
        # the norm squared of the sample vector from which it was
        # computed.
        
        samples = sound.samples
        num_samples = len(samples)
        
        (window, hop_size, dft_size, ref_power) = \
            (params.window, params.hop_size, params.dft_size, params.ref_power)
            
        window_size = len(window)
        
        if dft_size is None:
            dft_size = _get_dft_size(window_size)
            
        if num_samples < window_size:
            num_spectra = 0
        else:
            num_spectra = int(math.floor((num_samples - window_size) / \
                                         float(hop_size)) + 1)
            
        spectra = np.zeros((num_spectra, dft_size / 2 + 1), dtype='float32')
        
        x = np.zeros(dft_size, dtype='float32')
        
        # To ensure that for a rectangular window the sum of the bins
        # of each computed spectrum equals the norm squared of the
        # sample vector from which the spectrum was computed, we
        # scale the entire spectrum by `1. / dft_size` and we scale
        # all but the first and last bins by an additional factor
        # of two. The latter scaling is to include energy from the
        # negative frequency bins (the first and last bins, whose
        # center frequencies are zero and half the sample rate, have
        # no corresponding negative frequency bins). For efficiency
        # reasons, we perform these scalings first by scaling all
        # bins by `2. / dft_size`, and subsequently dividing the
        # first and last bins by two.
        scale_factor = 2. / dft_size
        
        j = 0
        
        for i in xrange(num_spectra):
            
            x[:window_size] = samples[j:(j + window_size)] * window
            dft = np.fft.rfft(x)
            spectra[i, :] = scale_factor * (dft * dft.conj()).real
            
            j += hop_size
            
        # Correct scaling of bins centered at zero frequency and
        # half the sample rate.
        spectra[:, 0] /= 2
        spectra[:, -1] /= 2
        
        if ref_power is not None:
            
            # TODO: If the following is unacceptably slow, implement a fast
            # replacement, for example using Cython or a NumPy ufunc.
            
            # We substitute `_SMALL_POWER` for small values in the gram
            # before taking logs to avoid divide by zero error messages
            # in the call to `np.log10`, and to avoid minus infinity
            # values in the output. Having large negative numbers is
            # preferable to having infinities since the latter do not
            # play well with other numbers in subsequent arithmetic
            # (for example 0 times infinity is `NaN`).
            
            spectra /= ref_power
            spectra[spectra < _SMALL_POWER] = _SMALL_POWER
            spectra = 10. * np.log10(spectra)
            
        sample_rate = float(sound.sample_rate)
    
        self.sound = sound
        self.window = window
        self.window_size = window_size
        self.hop_size = hop_size
        self.dft_size = dft_size
        self.ref_power = ref_power
        self.spectra = spectra
        self.frame_rate = sample_rate / hop_size
        self.max_freq = sample_rate / 2
        
        (self.num_spectra, self.num_bins) = spectra.shape
        self._spectrum_times = None
        self._bin_freqs = None
        self._min_value = None
        self._max_value = None
        
        self._interpolator = None
        
        
    @property
    def spectrum_times(self):
        
        if self._spectrum_times is None:
            offset = self.window_size / 2. / self.sound.sample_rate
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
        
        
def _get_dft_size(window_size):
    
    """Returns the smallest power of two that is at least `window_size`."""
    
    dft_size = 1
    while dft_size < window_size:
        dft_size <<= 1
    return dft_size
