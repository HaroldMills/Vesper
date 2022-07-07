"""Module containing class `RamSignal`."""


from numbers import Number

from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis


class RamSignal(Signal):
    
    """
    `Signal` whose samples are stored in random access memory (RAM).
    
    The samples are stored in a NumPy array. The array can be one that
    is indexed either frame-first or channel-first.
    """
    
    
    def __init__(self, time_axis, samples, frame_first, name=None):
        
        length, channel_count, item_shape =  _get_shape(samples, frame_first)
            
        time_axis = _get_time_axis(time_axis, length)
            
        super().__init__(
            time_axis, channel_count, item_shape, samples.dtype, name)

        self._samples = samples
        self._frame_first = frame_first


    def _read(self, frame_slice, channel_slice):

        if self._frame_first:
            samples = self._samples[frame_slice, channel_slice]
        else:
            samples = self._samples[channel_slice, frame_slice]

        return samples, self._frame_first


def _get_shape(samples, frame_first):
    
    shape = samples.shape
    
    if len(shape) < 2:
        raise ValueError(
            'RamSignal sample array must have at least two dimensions.')

    if frame_first:
        frame_count, channel_count = shape[:2]
    else:
        channel_count, frame_count = shape[:2]
        
    item_shape = shape[2:]
    
    return frame_count, channel_count, item_shape


def _get_time_axis(time_axis, length):

    if isinstance(time_axis, Number):
        # `time_axis` is frame rate

        return TimeAxis(length, time_axis)

    elif isinstance(time_axis, TimeAxis):
        
        if length != time_axis.length:
            raise ValueError(
                f'Number of sample frames {length} in NumPy sample '
                f'array does not match time axis length {time_axis.length}.')

        return time_axis

    else:
        raise TypeError(
            f'Expected either TimeAxis object or numeric frame rate, '
            f'but got {time_axis.__class__.__name__}.')
