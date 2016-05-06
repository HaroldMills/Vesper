"""Module containing class `Signal`."""


from vesper.signal.named_sequence import NamedSequence
from vesper.util.named import Named


class Signal(Named):
    
    
    def __init__(
            self, name, parent, time_axis, array_axes, amplitude_axis):
        
        super(Signal, self).__init__(name)
        
        self._parent = parent
        
        self._time_axis = time_axis
        self._array_axes = NamedSequence(array_axes)
        self._amplitude_axis = amplitude_axis
        
        self._index_axes = (time_axis,) + tuple(array_axes)
        axes = self._index_axes + (amplitude_axis,)
        self._axes = dict((a.name, a) for a in axes)
        
        
    @property
    def parent(self):
        return self._parent
    
    
    @property
    def time_axis(self):
        return self._time_axis
    
    
    @property
    def array_axes(self):
        return self._array_axes
    
    
    @property
    def amplitude_axis(self):
        return self._amplitude_axis
    
    
    @property
    def axes(self):
        return self._axes
    
    
    @property
    def dtype(self):
        raise NotImplementedError()
    
    
    @property
    def shape(self):
        return tuple(a.length for a in self._index_axes)
    
    
    def __len__(self):
        return self.time_axis.length
    
    
    def __getitem__(self, key):
        raise NotImplementedError()
