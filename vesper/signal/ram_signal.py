"""Module containing class `RamSignal`."""


from numbers import Number

from vesper.signal.sample_provider import SampleProvider
from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis


class RamSignal(Signal):
    
    """
    `Signal` whose samples are stored in random access memory (RAM).
    
    The samples are stored in a NumPy array. The array can be one that
    is indexed either frame-first or channel-first.
    """
    
    
    def __init__(self, time_axis, samples, frame_first, name=None):
        
        frame_count, channel_count, array_shape = \
            _get_shape(samples, frame_first)
            
        # Create `TimeAxis` from frame rate if needed.
        if isinstance(time_axis, Number):
            time_axis = TimeAxis(frame_count, time_axis)
        else:
            _check_frame_count(frame_count, time_axis)
            
        sample_provider = _SampleProvider(samples, frame_first)
        
        super().__init__(
            time_axis, channel_count, array_shape, samples.dtype,
            sample_provider, name)
        
        
def _get_shape(samples, frame_first):
    
    shape = samples.shape
    
    if len(shape) < 2:
        raise ValueError(
            'RamSignal NumPy sample array must have at least two dimensions.')

    if frame_first:
        frame_count, channel_count = shape[:2]
    else:
        channel_count, frame_count = shape[:2]
        
    array_shape = shape[2:]
    
    return frame_count, channel_count, array_shape


def _check_frame_count(frame_count, time_axis):
    
    if frame_count != time_axis.length:
        raise ValueError(
            f'Number of sample frames {frame_count} in NumPy sample '
            f'array does not match time axis length {time_axis.length}.')


class _SampleProvider(SampleProvider):
    
    def __init__(self, samples, frame_first):
        super().__init__(frame_first)
        self._samples = samples
        
    def get_samples(self, first_key, second_key):
        return self._samples[first_key, second_key]
