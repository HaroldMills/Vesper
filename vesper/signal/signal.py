"""Module containing class `Signal`."""


import numpy as np

from vesper.signal.channel import Channel
from vesper.signal.named_sequence import NamedSequence
from vesper.signal.signal_indexer import SignalIndexer
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

s.item_shape            # item shape

s.dtype                 # NumPy `dtype` of samples

s.read(start_frame_index, length, channel_indices=None)   
                        # synchronous sample read, raises exception if
                        # any existent, requested samples are unavailable

s.as_channels           # channel-first signal indexer
s.as_frames             # frame-first signal indexer
'''


# TODO: Make signal name mutable?


class Signal(Named):
    
    """
    Abstract base class of multichannel, multidimensional signals.
    
    Provides access to signal samples and associated metadata.

    A signal is a sequence of *sample frames* (or just *frames*),
    where a sample frame is a sequence of *items*, and an item
    is an n-dimensional array of numeric *samples*. All of the
    sample frames of a signal have the same length, and all of
    the items of a signal have the same dimensions. The number
    of dimensions of the items of a signal is the *dimensionality*
    of the signal. A zero-dimensional signal is also called a
    *scalar signal* or a *waveform*, and a one-dimensional signal
    is also called a *vector signal* or a *gram*. A two-dimensional
    signal is also called a *video*.

    All of the samples of a signal have same type, the signal's
    *sample type*. Common sample types are 16-bit integers and
    32-bit floating point numbers.

    The number of items per sample frame of a signal is the
    *channel count* of the signal. The sequence comprising the ith
    item of each frame of a signal, with the items in the same order
    as the frames to which they belong, is the ith *channel* of the
    signal.

    Each sample frame of a signal has an associated elapsed time
    in seconds. The sample frames of a signal are evenly spaced
    in time, with the times increasing by the signal's *frame
    period* from one frame to the next. The reciprocal of a signal's
    frame period is the signal's *frame rate*. The frame period
    and frame rate have units of seconds and hertz, respectively.
    The frame period and frame rate of a signal are frequently
    also referred to as its *sample period* and its *sample rate*,
    respectively, especially for waveforms.
    
    This class supports two methods of indexing the samples of a signal,
    corresponding to two different perspectives. According to the
    first perspective, called the *frame-first* perspective, a signal
    is a sequence of sample frames as described above, and the indices
    of a sample comprise first its frame index, followed by its channel
    index, followed by its item indices. According to the second
    perspective, called the *channel-first* perspective, a signal is
    a sequence of channels, each of which is a sequence of items, and
    the order of the first two indices of a sample are the reverse
    of what they are from the frame-first perspective. That is, the
    indices of a sample comprise first the channel index, followed
    by the frame index, followed by the item indices.

    TODO: Document read methods and revise the two paragraphs below.

    The samples of a signal are read via a *signal indexer*, an
    auxiliary object provided by the signal. Every signal offers
    two sample indexers. One, accessed via the `as_frames` signal
    property, supports frame-first indexing, while the other, accessed
    via the `as_channels` property, supports channel-first indexing.

    The channels of a signal are represented by `Channel` objects,
    accessed via the `channels` signal property. The samples of a
    channel can be read via a `Channel` as well as via signal indexers
    as described above.
    """
    
    
    def __init__(self, time_axis, channel_count, item_shape, dtype, name=None):
        
        if name is None:
            name = 'Signal'
            
        super().__init__(name)
        
        self._time_axis = time_axis
        self._channels = self._create_channels(channel_count)
        self._item_shape = tuple(item_shape)
        self._dtype = np.dtype(dtype)
        self._as_frames = SignalIndexer(self, True)
        self._as_channels = SignalIndexer(self, False)
        
        
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
    def item_shape(self):
        return self._item_shape
    
    
    @property
    def dtype(self):
        return self._dtype
    
    
    @property
    def as_frames(self):
        return self._as_frames
    
    
    @property
    def as_channels(self):
        return self._as_channels


    def read(
            self, start_frame_index=0, length=None, channel_indices=None,
            frame_first=True):

        if length is not None and length < 0:
            raise ValueError(
                f'Bad read length {length}. Length must be at least zero.')

        # Get frame and channel slices for call to `_read`.
        frame_slice = self._get_frame_slice(start_frame_index, length)
        channel_slice, result_channel_indices = \
            self._get_channel_slice(channel_indices)

        # Read samples.
        samples, samples_frame_first = self._read(frame_slice, channel_slice)

        # Select result channels if needed.
        if result_channel_indices is not None:
            samples = self._select_channels(
                samples, samples_frame_first, result_channel_indices)

        # Swap frame and channel axes if needed.
        if frame_first != samples_frame_first:
            samples = samples.swapaxes(0, 1)

        return samples
        

    def _get_frame_slice(self, start_index, length):

        if length is None:
            end_index = len(self)
        else:
            end_index = start_index + length

        start_index = self._clip_frame_index(start_index)
        end_index = self._clip_frame_index(end_index)

        return slice(start_index, end_index)


    def _clip_frame_index(self, index):

        if index < 0:
            return 0

        elif index > len(self):
            return len(self)

        else:
            return index


    def _get_channel_slice(self, indices):

        if indices is None:
            return slice(0, self.channel_count), None

        elif isinstance(indices, int):
            return slice(indices, indices + 1), None

        else:
            # assume `indices` is sequence of integers

            start_index = min(indices)
            end_index = max(indices) + 1
            result_slice = slice(start_index, end_index)
            result_indices = [i - start_index for i in indices]
            return result_slice, result_indices


    def _read(self, frame_slice, channel_slice):
        raise NotImplementedError()
    

    def _select_channels(self, samples, frame_first, indices):
        if frame_first:
            return samples[:, indices]
        else:
            return samples[indices, :]
