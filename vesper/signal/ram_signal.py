"""Module containing class `RamSignal`."""


from numbers import Number

import numpy as np

from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis


class RamSignal(Signal):
    
    """
    `Signal` whose samples are stored in random access memory (RAM).
    
    The samples are stored in a NumPy array. The array can be one that
    is indexed either frame-first or channel-first.
    """
    
    
    def __init__(
            self, samples, time_axis, name=None, samples_channel_first=False):
        
        self._samples = samples
        self._samples_channel_first = samples_channel_first
        
        self._as_frames, self._as_channels = \
            _get_sample_views(samples, samples_channel_first)
 
        shape = self._as_frames.shape
        frame_count = shape[0]
        channel_count = shape[1]
        array_shape = shape[2:]
        
        # Create `TimeAxis` from frame rate if needed.
        if isinstance(time_axis, Number):
            time_axis = TimeAxis(frame_count, time_axis)
            
        super().__init__(
            time_axis, channel_count, array_shape, samples.dtype, name)
        
        
    @property
    def samples(self):
        return self._samples
    
    
    @property
    def samples_channel_first(self):
        return self._samples_channel_first
    
    
    @property
    def as_frames(self):
        return self._as_frames
    
    
    @property
    def as_channels(self):
        return self._as_channels


def _get_sample_views(samples, samples_channel_first):
    
    if samples_channel_first:
        # first `samples` index is channel number
        
        as_channels, as_frames = _get_sample_views_aux(samples)
            
    else:
        # first `samples` index is frame number
        
        as_frames, as_channels = _get_sample_views_aux(samples)
            
    return as_frames, as_channels
            
            
def _get_sample_views_aux(samples):
        
    shape = samples.shape
    
    if len(shape) == 0:
        raise ValueError(
            'RamSignal sample NumPy array must have at least one dimension.')
    
    if len(shape) == 1:
        # `samples` has only one dimension
        
        # Append unit dimension to `samples` shape.
        samples = samples.reshape((shape[0], 1))
                
    # Create `samples` view with first two axes swapped.
    swapped = np.swapaxes(samples, 0, 1)
    
    return samples, swapped
