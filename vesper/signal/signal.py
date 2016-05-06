"""Module containing class `Signal`."""


from vesper.signal.signal_base import SignalBase


class Signal(SignalBase):
    
    """Abstract base class for signal classes."""
    
    
    def __init__(self, name, parent, time_axis, array_axes, amplitude_axis):
        super().__init__(name, time_axis, array_axes, amplitude_axis)
        self._parent = parent
        
        
    @property
    def parent(self):
        return self._parent

    
    @property
    def shape(self):
        time_axis_length = len(self)
        array_axis_lengths = tuple(a.length for a in self.array_axes)
        return (time_axis_length,) + array_axis_lengths
    
    
    def __len__(self):
        return self.time_axis.length
