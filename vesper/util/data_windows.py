"""Module containing data window definitions."""


import numpy as np


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
