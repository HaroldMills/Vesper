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


# from scipy import interpolate
import numpy as np


# TODO: Consider using more standard terminology, like "frames" instead
# of "analyses" and "frame rate" instead of "analysis rate".

# TODO: Consider having a time/frequency analysis always have a start
# time, which is the time of its first frame. Consider having the
# start time always be defined, even if the analysis has no frames.
# I believe this should work, since the time of the first frame
# can be computed from the input signal's frame rate and start time
# and the analysis window size and hop size, even if the input signal
# is too short for the analysis to have any frames.

# TODO: Consider unifying time/frequency analyses and audio segments.

# TODO: Figure out how to deal with multichannel signals. It will be
# important to figure this out early in the game, before we write lots
# of code that would be difficult to rewrite. I lean toward making a
# multichannel signal just be an array of single-channel signals, perhaps
# with certain additional metadata. More often than not we process the
# channels of a multichannel signal independently, and this will be both
# faster and more natural if the channel signals are separate. A good
# question to ask is how do the interfaces for single-channel signals
# and multi-channel signals relate to each other? For example, what is
# is the interface for reading samples in the two cases?


# TODO: Make `analyses` a property and compute spectra lazily?
class TimeFrequencyAnalysis(object):
    
    
    def __init__(self, audio, window, hop_size, freqs):
        
        self.audio = audio
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
        return float(self.audio.sample_rate) / self.hop_size
         

    @property
    def times(self):
        if self._times is None:
            audio = self.audio
            window = self.window
            offset = (window.size - 1) / 2. / audio.sample_rate
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
     
     
#     def interpolate(self, times, freqs):
#          
#         if self._interpolator is None:
#             self._interpolator = interpolate.RectBivariateSpline(
#                 self.times, self.freqs, self.analyses, kx=1, ky=1)
#              
#         return self._interpolator(times, freqs)
