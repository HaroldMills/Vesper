"""Module containing class `Channel`."""


from numbers import Number

from vesper.util.named import Named


'''
c.name

c.signal

c.number

c.time_axis            # `TimeAxis`

c.array_shape          # sample array shape

c.dtype                # NumPy `dtype` of samples

len(c)                 # number of sample arrays

c.shape

c[...]                 # frame index first, yields NumPy array of samples
'''


# TODO: Make channel name mutable?


class Channel(Named):
    
    """
    One channel of a signal.
    
    A channel is a sequence of sample arrays and associated metadata.
    """
    

    def __init__(self, signal, number, name=None):
        
        if name is None:
            name = str(number)
            
        super().__init__(name)
        
        self._signal = signal
        self._number = number

        
    @property
    def signal(self):
        return self._signal
    
    
    @property
    def number(self):
        return self._number
    
    
    @property
    def time_axis(self):
        return self.signal.time_axis
    
    
    @property
    def array_shape(self):
        return self.signal.array_shape
    
    
    @property
    def dtype(self):
        return self.signal.dtype
    
    
    @property
    def shape(self):
        return (len(self),) + self.array_shape
    
    
    def __len__(self):
        return len(self.signal)
    
    
    def __getitem__(self, key):
        
        # Build `Signal.as_channels` key from `Channel` key.
        if isinstance(key, tuple):
            key = (self.number,) + key
        else:
            key = (self.number, key)
            
        return self.signal.as_channels[key]
