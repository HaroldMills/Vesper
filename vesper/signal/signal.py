"""Module containing class `Signal`."""


import numpy as np

from vesper.signal.channel import Channel
from vesper.signal.named_sequence import NamedSequence
from vesper.util.named import Named


'''
s.name

s.time_axis            # `TimeAxis`

s.channels             # `NamedSequence` of `Channel` objects

s.array_shape          # sample array shape

s.dtype                # NumPy `dtype` of samples

s.as_frames            # indexed frame-first to yield Numpy arrays
s.as_channels          # indexed channel-first to yield NumPy arrays
'''


# TODO: Make signal name mutable?


class Signal(Named):
    
    """
    Abstract base class of multichannel, multidimensional signals.
    
    Provides access to signal samples and associated metadata.

    The `Signal` class is agnostic about whether a signal is a sequence
    of sample frames (the *frame view* of a signal) or a sequence of
    channels (the *channel view* of a signal). It supports both
    frame-first and channel-first indexing via the `as_frames` and
    `as_channels` properties, respectively.
    """
    
    
    def __init__(
            self, time_axis, channel_count, array_shape, dtype, name=None):
        
        if name is None:
            name = 'Signal'
            
        super().__init__(name)
        
        self._time_axis = time_axis
        self._channels = self._create_channels(channel_count)
        self._array_shape = tuple(array_shape)
        self._dtype = np.dtype(dtype)
        
        
    def _create_channels(self, channel_count):
        channels = [Channel(self, i) for i in range(channel_count)]
        return NamedSequence(channels)
        
        
    @property
    def time_axis(self):
        return self._time_axis
    
    
    @property
    def channels(self):
        return self._channels
    
    
    @property
    def array_shape(self):
        return self._array_shape
    
    
    @property
    def dtype(self):
        return self._dtype
    
    
    @property
    def as_frames(self):
        raise NotImplementedError()
    
    
    @property
    def as_channels(self):
        raise NotImplementedError()
