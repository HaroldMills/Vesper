"""Module containing `ArrayMultichannelSignal` class."""


import numpy as np

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_signal import ArraySignal
from vesper.signal.array_axis import ArrayAxis
from vesper.signal.multichannel_signal import MultichannelSignal
from vesper.signal.time_axis import TimeAxis


class ArrayMultichannelSignal(MultichannelSignal):
    
    
    def __init__(
            self, name=None, channel_names=None, time_axis=None,
            array_axes=None, amplitude_axis=None, samples=None):
        
        if samples is None:
            samples = np.array([], dtype='int16')
            
        shape = samples.shape
        num_channels = shape[0] if len(shape) > 0 else 0
        
        if channel_names is None:
            channel_names = \
                tuple('Channel ' + str(i) for i in range(num_channels))
            
        if time_axis is None:
            length = shape[1] if len(shape) > 1 else 0
            time_axis = TimeAxis(length=length)
            
        if array_axes is None:
            array_axes = tuple(ArrayAxis(length=n) for n in shape[1:])
                
        if amplitude_axis is None:
            amplitude_axis = AmplitudeAxis()
            
        # We check for shape consistency before creating the channel
        # signals since otherwise the `ArraySignal` initializer may
        # detect and report a shape inconsistency itself. It is more
        # desirable for `ArrayMultichannelSignal` to report the problem,
        # since its error message makes more sense in the context of
        # `ArrayMultichannelSignal` initialization.
        self._check_shape_consistency(
            num_channels, time_axis, array_axes, samples)
        
        channels = tuple(
            ArraySignal(
                channel_names[i], self, time_axis, array_axes, amplitude_axis,
                samples[i])
            for i in range(num_channels))
            
        super().__init__(name, channels, time_axis, array_axes, amplitude_axis)
        
        self._samples = samples
        
        
    def _check_shape_consistency(
            self, num_channels, time_axis, array_axes, samples):
        
        array_axis_lengths = tuple(a.length for a in array_axes)
        shape = (num_channels, time_axis.length) + array_axis_lengths
        
        if samples.shape != shape:
            raise ValueError((
                'Shape {} of samples differs from shape {} required by '
                'number of channels and axis lengths.').format(
                    samples.shape, shape))


    @property
    def dtype(self):
        return self._samples.dtype
    
    
    def __getitem__(self, key):
        return self._samples.__getitem__(key)
