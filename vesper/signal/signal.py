"""Module containing class `Signal`."""


import numpy as np

from vesper.signal.channel import Channel
from vesper.signal.indexer import Indexer
from vesper.signal.named_sequence import NamedSequence
from vesper.util.named import Named


'''
s.name

s.time_axis            # `TimeAxis`

s.channels             # `NamedSequence` of `Channel` objects

s.array_shape          # sample array shape

s.dtype                # NumPy `dtype` of samples

s.as_frames            # frame-first indexer yielding Numpy sample arrays
s.as_channels          # channel-first indexer yielding NumPy sample arrays
'''


# TODO: Make signal name mutable?


class Signal(Named):
    
    """
    Abstract base class of multichannel, multidimensional signals.
    
    Provides access to signal samples and associated metadata.

    A signal can be viewed and indexed according to two perspectives.
    According to the *frame perspective*, a signal is a sequence of
    sample frames and is indexed *frame-first*, with the first two
    indices specifying the frame number and channel number, respectively.
    According to the *channel perspective*, a signal is a sequence of
    channels and is indexed *channel-first*, with the first two indices
    specifying the channel number and frame number, respectively. As
    far as indexing is concerned, the difference between the two
    perspectives is just the order of the first two indices.
    
    The `Signal` class is agnostic with regard to these two perspectives,
    supporting both and favoring neither. A `Signal` object itself cannot
    be indexed directly (since that would entail favoring one of the two
    perspectives), but instead is indexed via a *signal indexer*. Every
    signal has two indexers, which are available as the signal's
    `as_frames` and `as_channels` properties. The `as_frames` indexer
    supports frame-first indexing, while the `as_channels` indexer
    supports channel-first indexing.
    """
    
    
    def __init__(
            self, time_axis, channel_count, array_shape, dtype,
            sample_provider, name=None):
        
        if name is None:
            name = 'Signal'
            
        super().__init__(name)
        
        self._time_axis = time_axis
        self._channels = self._create_channels(channel_count)
        self._array_shape = tuple(array_shape)
        self._dtype = np.dtype(dtype)
        self._sample_provider = sample_provider
        self._as_frames = Indexer(self, True)
        self._as_channels = Indexer(self, False)
        
        
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
        return self._as_frames
    
    
    @property
    def as_channels(self):
        return self._as_channels
