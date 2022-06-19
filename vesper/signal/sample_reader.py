"""Module containing class `SampleReader`."""


import numpy as np


'''
A `SampleReader` provides read access to the samples of a signal.
It is intended for use as a signal attribute, and not as a standalone
signal "flavor", so it has a minimal set of attributes. Signal
metadata like the time axis and the sample aray shape are available as
attributes of a reader's signal but not as attributes of the reader
itself.


r.signal

r.frame_first      # `true` if and only if reader is frame-first

len(r)             # channel count if channel-first, frame count if
                   # frame-first

r.shape            # first two elements ordered according to reader type

r.sample_type      # NumPy `dtype` of samples

r[...]             # synchronous, reads one signal segment, raises exception
                   # if not all of segment available

r.read(...)        # asynchronous, can read multiple segments, yields
                   # intersection of requested segments and available
                   # segments
'''


class SampleReader:
    
    """
    Signal sample reader.
    
    A sample reader provides read-only access to the samples of a
    signal. Reads can be either synchronous or asynchronous.
    Synchronous reads are accomplished by indexing a reader much
    like a NumPy array, yielding a NumPy array of samples.
    
    A sample reader is of one of two types, called *frame-first* and
    *channel-first*. For both types, the first two indices specified
    for a read refer to the signal frame and channel numbers, but for
    a frame-first reader the frame number is specified first,
    preceding the channel number, while for a channel-first reader
    the channel number is specified first, preceding the frame number.
    
    A sample reader translates a call to its `__getitem__` method to a
    call to the `read` method of its signal's sample read delegate.
    The reader handles matters like `__getitem__` argument type and
    range checking, normalization, and (if needed) reordering so the
    read delegate doesn't have to. This simplifies `Signal` subclass
    implementation considerably.
    """
    
    
    def __init__(self, signal, frame_first):
        self._signal = signal
        self._frame_first = frame_first
        self._read_delegate = signal._read_delegate
        self._normalize_args = self._get_normalize_args()
        
        
    def _get_normalize_args(self):
        
        """
        Creates a table of two pairs of positional arguments for the
        `_normalize_int_or_slice_key` function. The table is indexed
        by zero to obtain arguments for normalizing the first reader
        key (the frame key when the reader is frame-first and the
        channel key when it is channel-first) and by one to obtain
        arguments for normalizing the second reader key (the channel
        key when the reader is frame-first and the frame key when it
        is channel-first). 
        """
        
        frame_count = self.signal.time_axis.length
        channel_count = len(self.signal.channels)
        
        if self.frame_first:
            return ((frame_count, 'time'), (channel_count, 'channel'))
        else:
            return ((channel_count, 'channel'), (frame_count, 'time'))
        
        
    @property
    def signal(self):
        return self._signal
    
    
    @property
    def frame_first(self):
        return self._frame_first
    
    
    def __len__(self):
        if self.frame_first:
            return self.signal.time_axis.length
        else:
            return len(self.signal.channels)
        

    @property
    def shape(self):
        
        frame_count = self.signal.time_axis.length
        channel_count = len(self.signal.channels)
        array_shape = self.signal.array_shape
        
        if self.frame_first:
            return (frame_count, channel_count) + array_shape
        else:
            return (channel_count, frame_count) + array_shape
        
        
    @property
    def dtype(self):
        return self.signal.dtype
    
    
    def __getitem__(self, key):
        
        _check_key_type(key)
        
        first_key, second_key, samples_key = self._get_keys(key)
        
        # Get requested sample arrays from read delegate.
        samples = self._read_delegate.read(first_key, second_key)

        # Index sample arrays if specified.
        if samples_key is not None:
            samples = samples[samples_key]
        
        # Swap first two axes of result if needed.
        if self.frame_first != self._read_delegate.frame_first and \
                isinstance(first_key, slice) and isinstance(second_key, slice):
            samples = np.swapaxes(samples, 0, 1)
        
        return samples
    
    
    def _get_keys(self, key):
        
        # Get keys assuming read delegate and reader index orders are
        # the same.
        if isinstance(key, tuple):
            first_key = key[0]
            second_key = key[1]
            samples_key = key[2:] if len(key) > 2 else None
        else:
            first_key = key
            second_key = slice(None)
            samples_key = None
        
        # Normalize first and second keys.
        normalize = _normalize_int_or_slice_key
        first_key = normalize(first_key, *self._normalize_args[0])
        second_key = normalize(second_key, *self._normalize_args[1])
            
        # Swap first and second keys if read delegate and reader index
        # orders differ.
        if self._read_delegate.frame_first != self.frame_first:
            temp = first_key
            first_key = second_key
            second_key = temp
            
        # Prepend colon slices to samples key if first and/or second
        # keys are slices.
        if samples_key is not None:
            for k in (second_key, first_key):
                if isinstance(k, slice):
                    samples_key = (slice(None),) + samples_key
            
        return first_key, second_key, samples_key


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


def _normalize_int_or_slice_key(key, length, axis_name=None):
    if isinstance(key, int):
        return _normalize_int_key(key, length, axis_name)
    else:
        return _normalize_slice_key(key, length)
    
    
def _normalize_int_key(key, length, axis_name=None):
        
    """
    Normalizes an integer signal key.
    
    Leaves a nonnegative key as it is, but converts a negative key to
    the equivalent nonnegative one.
    """
    
    axis_text = '' if axis_name is None else axis_name + ' '
    
    if key < -length or key >= length:
        raise IndexError(
            f'Index {key} is out of bounds for signal {axis_text}axis with '
            f'length {length}.')
        
    return key if key >= 0 else key + length


def _normalize_slice_key(key, length):
        
    if key.step is not None and key.step != 1:
        raise IndexError(
            f'Unsupported signal slice step size {key.step}. '
            f'The only supported step size is one.')
    
    start = _normalize_slice_bound(key.start, 0, length)
    stop = _normalize_slice_bound(key.stop, length, length)
    
    if stop < start:
        stop = start
        
    return slice(start, stop)


def _normalize_slice_bound(bound, default, length):
    
    if bound is None:
        bound = default
    
    elif bound < 0:
        
        bound += length
        
        if bound < 0:
            bound = 0

    elif bound > length:
        bound = length
    
    return bound
