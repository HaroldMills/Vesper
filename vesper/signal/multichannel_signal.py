"""Module containing class `MultichannelSignal`."""


from vesper.signal.named_sequence import NamedSequence
from vesper.signal.signal_base import SignalBase


class MultichannelSignal(SignalBase):
    
    """Abstract base class for multichannel signal classes."""
    
    
    def __init__(self, name, channels, time_axis, array_axes, amplitude_axis):
        super().__init__(name, time_axis, array_axes, amplitude_axis)
        self._channels = NamedSequence(channels)
        
        
    @property
    def channels(self):
        return self._channels
    
    
    @property
    def shape(self):
        num_channels = len(self)
        time_axis_length = self.time_axis.length
        array_axis_lengths = tuple(a.length for a in self.array_axes)
        return (num_channels, time_axis_length) + array_axis_lengths
    
    
    def __len__(self):
        return len(self.channels)
