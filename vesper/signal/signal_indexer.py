"""Module containing class `SignalIndexer`."""


import math


'''
A `SignalIndexer` provides NumPy-array-like access to the samples
of a signal. It includes `shape`, `size`, and `dtype` properties and
`__len__` and `__getitem__` methods. Every signal provides two indexers,
one for frame-first indexing and the other for channel-first indexing.


r.signal

r.frame_first      # `true` if and only if indexer is frame-first

len(r)             # channel count if channel-first, frame count if
                   # frame-first

r.shape            # first two elements ordered according to whether
                   # indexer is frame-first or channel-first

r.size             # product of elements of `r.shape`.

r.dtype            # NumPy `dtype` of samples

r[...]             # synchronous, reads one signal segment, raises exception
                   # if not all of segment available
'''


# TODO: Consider enhancing `__getitem__` to support frame and channel
# slices with non-unit step sizes. The enhanced method would read a
# contiguous range of frames and channels with `Signal._read` and then
# slice the frame and channel axes of the result if needed.


_COLON_SLICE = slice(None)


class SignalIndexer:
    
    """
    Signal indexer.
    
    A `SignalIndexer` provides a `__getitem__` method that allows a
    signal to be indexed much like a NumPy array.
    
    A signal indexer is of one of two types, called *frame-first* and
    *channel-first*. For both types, the first two indices of an
    indexing operation are the sample frame and channel indices,
    but for a frame-first indexer the frame index is specified first,
    preceding the channel index, while for a channel-first indexer
    the channel index is specified first, preceding the frame index.
    Every signal provides two indexers via its `as_frames` and
    `as_channels` properties, the first for frame-first indexing
    and the second for channel-first indexing.
    
    A signal indexer translates a call to its `__getitem__` method to
    a call to its signal's `_read` method. The indexer handles matters
    like `__getitem__` index type checking, range checking, and
    normalization before calling the `_read` method.
    """
    
    
    def __init__(self, signal, frame_first):
        self._signal = signal
        self._frame_first = frame_first
        
        
    @property
    def signal(self):
        return self._signal
    
    
    @property
    def frame_first(self):
        return self._frame_first
    
    
    def __len__(self):
        if self.frame_first:
            return len(self.signal)
        else:
            return self.signal.channel_count
        

    @property
    def shape(self):
        
        frame_count = len(self.signal)
        channel_count = self.signal.channel_count
        item_shape = self.signal.item_shape
        
        if self.frame_first:
            return (frame_count, channel_count) + item_shape
        else:
            return (channel_count, frame_count) + item_shape
        
    
    @property
    def size(self):
        return math.prod(self.shape)


    @property
    def dtype(self):
        return self.signal.dtype
    
    
    def __getitem__(self, key):
        
        _check_key_type(key)
        
        # Get indexing information in a standard form.
        (frame_slice, frame_key_was_int, channel_slice, channel_key_was_int,
            item_key) = self._parse_key(key)
        
        # Get requested items from signal.
        samples, samples_frame_first = \
            self.signal._read(frame_slice, channel_slice)

        # Make frame axis first.
        if not samples_frame_first:
            samples = samples.swapaxes(0, 1)
            samples_frame_first = True

        # Index items if needed.
        if item_key is not None:
            samples = _index_items(samples, item_key)
        
        # Make sure result has correct axis count and order.
        return self._modify_result_axes_if_needed(
            samples, frame_key_was_int, channel_key_was_int)
    
    
    def _parse_key(self, key):
        
        # Get first, second, and samples indexing keys.
        if isinstance(key, tuple):
            first_key = key[0]
            second_key = key[1]
            samples_key = key[2:] if len(key) > 2 else None
        else:
            first_key = key
            second_key = _COLON_SLICE
            samples_key = None

        # Get frame and channel indexing keys.
        if self.frame_first:
            frame_key = first_key
            channel_key = second_key
        else:
            frame_key = second_key
            channel_key = first_key
        
        # Normalize frame and channel indexing keys.
        frame_slice, frame_key_was_int =  \
            _normalize_key(frame_key, len(self.signal), 'frame')
        channel_slice, channel_key_was_int = \
            _normalize_key(channel_key, self.signal.channel_count, 'channel')

        return (
            frame_slice, frame_key_was_int, channel_slice, channel_key_was_int,
            samples_key)


    def _modify_result_axes_if_needed(
            self, samples, frame_key_was_int, channel_key_was_int):

        """
        Modifies `samples` as needed so `__getitem__` result has
        correct number and order of axes.

        `samples` is always frame-first.
        """

        shape = samples.shape

        if frame_key_was_int and channel_key_was_int:
            # frame and channel keys were both integers

            # Drop frame and channel axes of `samples`.
            return samples.reshape(shape[2:])

        elif frame_key_was_int:
            # frame key was integer and channel key was slice

            # Drop frame axis of `samples`.
            return samples.reshape(shape[1:])

        elif channel_key_was_int:
            # frame key was slice and channel key was integer

            # Drop channel axis of `samples`.
            return samples.reshape((shape[0],) + shape[2:])

        else:
            # frame and channel keys were both slices
            
            if self.frame_first:
                # frame and channel axes of `samples` are in correct order

                return samples

            else:
                # need to swap frame and channel axes of `samples`

                return samples.swapaxes(0, 1)


def _check_key_type(key):
    
    if isinstance(key, int) or isinstance(key, slice):
        return
    
    elif isinstance(key, tuple):
        for k in key:
            if not (isinstance(k, int) or isinstance(k, slice)):
                _raise_key_type_error()
 
    else:
        _raise_key_type_error()
            
            
def _raise_key_type_error():
    raise TypeError(f'Only integers and slices are valid signal indices.')


def _normalize_key(key, length, name):
    if isinstance(key, int):
        return _normalize_int_key(key, length, name), True
    else:
        return _normalize_slice_key(key, length, name), False
    
    
def _normalize_int_key(key, length, name):
        
    """
    Normalizes an integer signal key.
    
    Leaves a nonnegative key as it is, but converts a negative key to
    the equivalent nonnegative one.
    """
    
    if key < -length or key >= length:
        raise IndexError(
            f'Signal {name} index {key} is out of range '
            f'[-{length}, {length}].')
        
    if key >= 0:
        start = key
    else:
        start = key + length

    return slice(start, start + 1)


def _normalize_slice_key(key, length, name):
        
    if key.step is not None and key.step != 1:
        raise IndexError(
            f'Unsupported signal {name} slice step size {key.step}. '
            f'The only supported step size is one.')
    
    start = _normalize_slice_bound(key.start, 0, length)
    stop = _normalize_slice_bound(key.stop, length, length)
    
    if stop < start:
        stop = start
        
    return slice(start, stop)


def _normalize_slice_bound(bound, default, length):
    
    # Note that in this function, if a bound is outside of the range
    # [0, length] (including after adding a negative bound to the
    # signal length) we clip it to that range and proceed. This is
    # different from how the `_normalize_int_key` function deals with
    # the analogous situation for integer keys, namely by raising an
    # `IndexError` exception. This is consistent with how integer
    # indexing and slicing work for many common Python classes that
    # support indexing, including tuples, lists, and NumPy arrays.

    if bound is None:
        bound = default
    
    elif bound < 0:
        
        bound += length
        
        if bound < 0:
            bound = 0

    elif bound > length:
        bound = length
    
    return bound


def _index_items(samples, samples_key):

    # Prepend two colon slices (i.e. what `__getitem__` receives when
    # you index with ":") to samples key to make `samples` key. The
    # added slices are for the time and channel axes.
    if isinstance(samples_key, tuple):
        key = (_COLON_SLICE, _COLON_SLICE) + samples_key
    else:
        key = (_COLON_SLICE, _COLON_SLICE, samples_key)

    return samples[key]
