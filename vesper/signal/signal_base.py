"""Module containing class `SignalBase`."""


from vesper.signal.named_sequence import NamedSequence
from vesper.util.named import Named


class SignalBase(Named):
    
    """Abstract base class for both signal and multichannel signal classes."""
    
    
    def __init__(self, name, time_axis, array_axes, amplitude_axis):
        
        super().__init__(name)
        
        self._time_axis = time_axis
        self._array_axes = NamedSequence(array_axes)
        self._amplitude_axis = amplitude_axis
        
        self._indexed_axes = (time_axis,) + tuple(array_axes)
        axes = self._indexed_axes + (amplitude_axis,)
        self._axes = dict((a.name, a) for a in axes)
        
        
    @property
    def time_axis(self):
        return self._time_axis
    
    
    @property
    def array_axes(self):
        return self._array_axes
    
    
    @property
    def amplitude_axis(self):
        return self._amplitude_axis
    
    
    @property
    def axes(self):
        return self._axes
    
    
    @property
    def dtype(self):
        raise NotImplementedError()
    
    
    @property
    def shape(self):
        raise NotImplementedError()
    
    
    def __len__(self):
        raise NotImplementedError()
    
    
    def __getitem__(self, key):
        raise NotImplementedError()
