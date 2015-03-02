"""
Abstract parent class for time-frequency analyses.

By a *time-frequency analysis*, we mean an analysis of a waveform that
produces an analysis vector for each of a sequence of regularly spaced,
windowed waveform segments. We refer to the spacing of the waveform
segments as the *hop size*, and to each of the analysis vectors as
an *analysis*.

Examples of common time-frequency analyses include the short-time
Fourier transform (STFT) and the spectrogram. Other examples include
sequences of phase spectra, vectors of instantaneous frequencies, etc.

[The use of the term "analysis" for each analysis vector of a
time-frequency analysis is awkward and potentially confusing, since we
also refer to the entire time-frequency analysis as an "analysis". Perhaps
there is another term we could use for the generalization of "spectrum"?
Or maybe we should just stick with "spectrum", but use it in a more general
sense?]
"""


from scipy import interpolate
import numpy as np


# TODO: Make `analyses` a property and compute spectra lazily?
class TimeFrequencyAnalysis(object):
    
    
    def __init__(self, sound, window, hop_size, freqs):
        
        self.sound = sound
        self.window = window
        self.hop_size = hop_size
        self.freqs = freqs
        
        self.analyses = self._analyze()
        
        self._times = None
        self._min_value = None
        self._max_value = None
        
        self._interpolator = None

        
    @property
    def analysis_rate(self):
        return float(self.sound.sample_rate) / self.hop_size
         

    @property
    def times(self):
        if self._times is None:
            sound = self.sound
            window = self.window
            offset = (window.size - 1) / 2. / sound.sample_rate
            num_analyses = len(self.analyses)
            self._times = offset + np.arange(num_analyses) / self.analysis_rate
        return self._times
        
        
    @property
    def min_value(self):
        if self._min_value is None and len(self.analyses) != 0:
            self._min_value = np.min(np.min(self.analyses))
        return self._min_value
     
     
    @property
    def max_value(self):
        if self._max_value is None and len(self.analyses) != 0:
            self._max_value = np.max(np.max(self.analyses))
        return self._max_value
    
    
    def _analyze(self):
        raise NotImplementedError()
     
     
    def interpolate(self, times, freqs):
         
        if self._interpolator is None:
            self._interpolator = interpolate.RectBivariateSpline(
                self.times, self.freqs, self.analyses, kx=1, ky=1)
             
        return self._interpolator(times, freqs)
