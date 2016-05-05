"""Module containing `ArraySignal` class."""


import numpy as np

from vesper.signal.signal import Signal
from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.sample_array_axis import SampleArrayAxis
from vesper.signal.time_axis import TimeAxis


class ArraySignal(Signal):
    
    
    def __init__(
            self, name=None, parent=None, time_axis=None,
            sample_array_axes=None, amplitude_axis=None, samples=None):
        
        if samples is None:
            samples = np.array([], dtype='int16')
            
        if time_axis is None:
            time_axis = TimeAxis(length=len(samples))
            
        if sample_array_axes is None:
            sample_array_axes = tuple(
                SampleArrayAxis(length=n) for n in samples.shape[1:])
                
        if amplitude_axis is None:
            amplitude_axis = AmplitudeAxis()
            
        super().__init__(
            name, parent, time_axis, sample_array_axes, amplitude_axis)
        
        self._samples = samples


    @property
    def dtype(self):
        return self._samples.dtype
    
    
    def __getitem__(self, key):
        return self._samples.__getitem__(key)
