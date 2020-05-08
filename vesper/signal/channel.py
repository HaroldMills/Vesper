"""Module containing class `Channel`."""


from vesper.util.named import Named


'''
A `Channel` is intended for use as a standalone object, and so has a
full set of attributes. For example, signal metadata like the time axis,
the sample array shape, and the sample dtype are available as channel
attributes, even though they are also available as attributes of the
channels' signal.


c.name

c.signal

c.number

c.time_axis            # `TimeAxis`

len(c)                 # sample array count, `c.time_axis.frame_count`

c.array_shape          # sample array shape

c.shape                # `(len(c),) + c.array_shape`

c.dtype                # NumPy `dtype` of samples

c[...]                 # frame index first, followed by sample array indices
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
    
    
    def __len__(self):
        return self.time_axis.frame_count
    
    
    @property
    def array_shape(self):
        return self.signal.array_shape
    
    
    @property
    def shape(self):
        return (len(self),) + self.array_shape
    
    
    @property
    def dtype(self):
        return self.signal.dtype
    
    
    def __getitem__(self, key):
        
        # Build `Signal.as_channels` key from `Channel` key.
        if isinstance(key, tuple):
            key = (self.number,) + key
        else:
            key = (self.number, key)
            
        return self.signal.as_channels[key]
