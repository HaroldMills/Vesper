"""Module containing class `Signal`."""


import numpy as np

from vesper.signal.channel import Channel
from vesper.signal.named_sequence import NamedSequence
from vesper.signal.sample_reader import SampleReader
from vesper.util.named import Named


'''
s.name

s.time_axis             # `TimeAxis`

s.frame_rate            # `s.time_axis.frame_rate`
s.frame_period          # `s.time_axis.frame_period`

s.sample_rate           # `s.time_axis.sample_rate`
s.sample_period         # `s.time_axis.sample_period`

len(s)                  # frame count, `s.time_axis.length`

s.channels              # `NamedSequence` of `Channel` objects
s.channel_count         # `len(s.channels)`

s.sample_array_shape    # sample array shape

s.sample_type           # NumPy `dtype` of samples

s.as_channels           # channel-first sample reader
s.as_frames             # frame-first sample reader
'''


# TODO: Make signal name mutable?


class Signal(Named):
    
    """
    Abstract base class of multichannel, multidimensional signals.
    
    Provides access to signal samples and associated metadata.

    A signal is a sequence of *sample frames*, where a sample frame
    is a sequence of numeric *sample arrays*. All of the sample
    frames of a signal have the same length, and all of the sample
    arrays of a signal have the same dimensions. The number of
    dimensions of the sample arrays of a signal is the
    *dimensionality* of the signal. A zero-dimensional signal is
    also called a *scalar signal* or a *waveform*, and a
    one-dimensional signal is also called a *vector signal* or a
    *gram*. A two-dimensional signal is also called a *video*.

    All of the samples of a signal have same type, the signal's
    *sample type*. Common sample types are 16-bit integers and
    32-bit floating point numbers.

    The number of sample arrays per sample frame of a signal is
    the *channel count* of the signal. The sequence comprising
    the ith sample array of each frame of a signal, with the
    sample arrays in the same order as the frames to which they
    belong, is the ith *channel* of the signal.

    Each sample frame of a signal has an associated elapsed time
    in seconds. The sample frames of a signal are evenly spaced
    in time, with the times increasing by the signal's *frame
    period* from one frame to the next. The reciprocal of a signal's
    frame period is the signal's *frame rate*. The frame period
    and frame rate have units of seconds and hertz, respectively.
    
    This class supports two methods of indexing the samples of a signal,
    corresponding to two different perspectives. According to the
    first perspective, called the *frame-first* perspective, a signal
    is a sequence of sample frames as described above, and the indices
    of a sample comprise first its frame number, followed by its channel
    number, followed by its sample array indices. According to the second
    perspective, called the *channel-first* perspective, a signal is
    a sequence of channels, each of which is a sequence of sample arrays,
    and the order of the first two indices of a sample are the reverse
    of what they are from the frame-first perspective. That is, the
    indices of a sample comprise first the channel number, followed
    by the frame number, followed by the sample array indices.

    The samples of a signal are read via a *sample reader*, an
    auxiliary object provided by the signal. Every signal offers
    two sample readers. One, accessed via the `as_frames` signal
    property, supports frame-first indexing, while the other, accessed
    via the `as_channels` property, supports channel-first indexing.

    The channels of a signal are represented by `Channel` objects,
    accessed via the `channels` signal property. The samples of a
    channel can be read via a `Channel` as well as via signal sample
    readers as described above.
    """
    
    
    def __init__(
            self, time_axis, channel_count, sample_array_shape, sample_type,
            read_delegate, name=None):
        
        if name is None:
            name = 'Signal'
            
        super().__init__(name)
        
        self._time_axis = time_axis
        self._channels = self._create_channels(channel_count)
        self._sample_array_shape = tuple(sample_array_shape)
        self._sample_type = np.dtype(sample_type)
        self._read_delegate = read_delegate
        self._as_frames = SampleReader(self, True)
        self._as_channels = SampleReader(self, False)
        
        
    def _create_channels(self, channel_count):
        channels = [Channel(self, i) for i in range(channel_count)]
        return NamedSequence(channels)
        
        
    @property
    def time_axis(self):
        return self._time_axis
    
    
    def __len__(self):
        return self.time_axis.length


    @property
    def frame_rate(self):
        return self.time_axis.frame_rate


    @property
    def frame_period(self):
        return self.time_axis.frame_period


    @property
    def sample_rate(self):
        return self.time_axis.sample_rate


    @property
    def sample_period(self):
        return self.time_axis.sample_period


    @property
    def channels(self):
        return self._channels


    @property
    def channel_count(self):
        return len(self.channels)
    
    
    @property
    def sample_array_shape(self):
        return self._sample_array_shape
    
    
    @property
    def sample_type(self):
        return self._sample_type
    
    
    @property
    def as_frames(self):
        return self._as_frames
    
    
    @property
    def as_channels(self):
        return self._as_channels
