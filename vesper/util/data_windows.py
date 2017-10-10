"""Module containing data window definitions."""


import numpy as np


'''
TODO: Reconsider data window classes and their relationship to
time frequency analyses. For example, it seems like it might be overly
restrictive for our `Spectrogram` class to require that the analysis
data window be specified via an object when all we use of that object
for the analysis is the `samples` NumPy array. Why not require only
the array? On the other hand, we do support spectorgram computation
with specification of the window as just a NumPy array in the
`time_frequency_analysis_utils.compute_spectrogram` function, and
it might be nice in the future to have relatively high-level
spectrogram objects that have settings like a window name, window
parameters (other than the length), etc.
'''


class HannWindow(object):
    
    name = 'Hann'
    
    def __init__(self, N):
        self.size = N
        phases = 2 * np.pi * np.arange(N) / float(N)
        self.samples = .5 - .5 * np.cos(phases)
        self.derivative = np.pi / N * np.sin(phases)
    
        
class RectangularWindow(object):
    
    name = 'Rectangular'
    
    def __init__(self, N):
        self.size = N
        self.samples = np.ones(N)
        self.derivative = np.zeros(N)
    
    
_WINDOW_TYPES = dict((t.name, t) for t in (HannWindow, RectangularWindow))


def create_window(name, N):
    
    try:
        window_type = _WINDOW_TYPES[name]
    except KeyError:
        raise ValueError('Unrecognized window type "{:s}".'.format(name))
    
    return window_type(N)
