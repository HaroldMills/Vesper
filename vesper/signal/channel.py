"""Module containing class `Channel`."""


import math

from vesper.util.named import Named


'''
A `Channel` is intended for use as a standalone object, and so has a
full set of attributes. For example, signal metadata like the time axis,
the item shape and size, and the sample type are available as channel
attributes, even though they are also available as attributes of the
channel's signal.


c.signal

c.index                 # channel index, in [0, `c.signal.channel_count`)

c.name

c.time_axis             # `c.signal.time_axis`

c.frame_rate            # `c.time_axis.frame_rate`
c.frame_period          # `c.time_axis.frame_period`

c.sample_rate           # `c.time_axis.sample_rate`
c.sample_period         # `c.time_axis.sample_period`

len(c)                  # item count, `c.time_axis.length`

c.item_shape            # item shape

c.shape                 # `(len(c),) + c.item_shape`

c.size                  # product of elements of `c.shape`

c.dtype                 # NumPy `dtype` of samples

c.read(start_index, length)
                        # synchronous sample read, raises exception
                        # if any requested samples are unavailable

c[...]                  # synchronous, delegates to `c.read`
'''


# TODO: Make channel name mutable?


class Channel(Named):
    
    """
    One channel of a signal.
    
    A channel is a sequence of items and associated metadata.
    """
    

    def __init__(self, signal, index, name=None):
        
        if name is None:
            name = str(index)
            
        super().__init__(name)
        
        self._signal = signal
        self._index = index

        
    @property
    def signal(self):
        return self._signal
    
    
    @property
    def index(self):
        return self._index
    
    
    @property
    def time_axis(self):
        return self.signal.time_axis


    def __len__(self):
        return len(self.signal)
    
    
    @property
    def frame_rate(self):
        return self.signal.frame_rate


    @property
    def frame_period(self):
        return self.signal.frame_period


    @property
    def sample_rate(self):
        return self.signal.sample_rate


    @property
    def sample_period(self):
        return self.signal.sample_period


    @property
    def item_shape(self):
        return self.signal.item_shape
    
    
    @property
    def shape(self):
        return (len(self),) + self.item_shape


    @property
    def size(self):
        return math.prod(self.shape)
    
    
    @property
    def dtype(self):
        return self.signal.dtype
    
    
    def read(self, start_item_index=0, length=None):
        return self.signal.read(start_item_index, length, self.index, False)[0]


    def __getitem__(self, key):
        
        # Build `Signal.as_channels` key from `Channel` key.
        if isinstance(key, tuple):
            key = (self.index,) + key
        else:
            key = (self.index, key)
            
        return self.signal.as_channels[key]
