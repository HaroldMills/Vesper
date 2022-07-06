"""Module containing class `Channel`."""


from vesper.util.named import Named


'''
A `Channel` is intended for use as a standalone object, and so has a
full set of attributes. For example, signal metadata like the time axis,
the sample array shape, and the sample type are available as channel
attributes, even though they are also available as attributes of the
channels' signal.


c.signal

c.number           # channel number, in [0, `c.signal.channel_count`)

c.name

c.time_axis             # `c.signal.time_axis`

c.frame_rate            # `c.time_axis.frame_rate`
c.frame_period          # `c.time_axis.frame_period`

c.sample_rate           # `c.time_axis.sample_rate`
c.sample_period         # `c.time_axis.sample_period`

len(c)                  # sample array count, `c.time_axis.length`

c.sample_array_shape    # sample array shape

c.shape                 # `(len(c),) + c.sample_array_shape`

c.sample_type           # NumPy `dtype` of samples

c.read(start_index, length)
                        # synchronous sample read, raises exception
                        # if any requested samples are unavailable

c[...]                  # synchronous, delegates to `c.read`
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
    def sample_array_shape(self):
        return self.signal.sample_array_shape
    
    
    @property
    def shape(self):
        return (len(self),) + self.sample_array_shape
    
    
    @property
    def sample_type(self):
        return self.signal.sample_type
    
    
    def __getitem__(self, key):
        
        # Build `Signal.as_channels` key from `Channel` key.
        if isinstance(key, tuple):
            key = (self.number,) + key
        else:
            key = (self.number, key)
            
        return self.signal.as_channels[key]
