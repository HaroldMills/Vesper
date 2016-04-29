import datetime

import numpy as np

from vesper.util.named import Named


class Signal(Named):
    
    
    def __init__(
            self, name, sample_type, sample_array_shape, length, start_index=0,
            origin_time=0, origin_datetime=None, sample_rate=1.):
        
        super(Signal, self).__init__(name)
        
        self._dtype = dtype
        self._sample_array_shape = sample_array_shape
        self._length = length
        self._start_index = start_index
        self._origin_time = origin_time
        self._origin_datetime = origin_datetime
        self._sample_rate = float(sample_rate)
        
        
    @property
    def dtype(self):
        return self._dtype
    
    
    @property
    def sample_array_shape(self):
        return self._sample_array_shape
    
    
    @property
    def sample_array_size(self):
        return int(np.prod(self.sample_array_shape))
    
    
    def __len__(self):
        
        """Gets the length of this signal in samples."""
        
        return self._length
    
    
    @property
    def shape(self):
        return (len(self),) + self.sample_array_shape
    
    
    @property
    def start_index(self):
        
        """
        the start index of this signal.
        
        The start index is a nonnegative integer.
        """
        
        return self._start_index
    
    
    @property
    def origin_time(self):
        
        """
        the time of the origin (sample zero) of this signal, in seconds.
        """
        
        return self._origin_time
    
    
    @property
    def origin_datetime(self):
        
        """
        the date and time of the origin (sample zero) of this signal,
        a `datetime`.
        
        The origin `datetime` is `None` if unknown.
        """
        
        return self._origin_datetime
    
    
    @property
    def sample_rate(self):
        """the sample rate of this signal, in hertz."""
        return self._sample_rate
    
    
    @property
    def sample_period(self):
        """the sample period of this signal, in seconds."""
        return 1. / self.sample_rate
    
    
    @property
    def duration(self):
        
        """
        the duration of this signal, in seconds.
        
        The duration of a signal is its length times its sample period.
        """
        
        return len(self) * self.sample_period
        
        
    def index_to_time(self, i):
        
        """
        Gets the time of the specified index, in seconds.
        
        The argument can be either a single index or a NumPy array
        of indices.
        
        The time of a signal index is the signal's origin time plus
        the index times the sample period.
        """
        
        return i * self.sample_period + self.origin_time
        
    
    def time_to_index(self, t):
        
        """
        Gets the index corresponding to the specified time.
        
        The argument can be either a single time or a NumPy array
        of times, in seconds.
        
        This method is the inverse of the `index_to_time` method.
        The resulting index is not rounded to an integer value.
        """
        
        return (t - self.origin_time) * self.sample_rate
    
    
    def index_to_datetime(self, i):
        
        """
        Gets the date and time of the specified index, as a `datetime`.
        
        The argument must be a single index.
        
        The date and time of a signal index is the signal's origin
        `datetime` plus the index times the sample period.
        """
        
        if self.origin_datetime is None:
            return None
        else:
            delta = datetime.timedelta(seconds=i * self.sample_period)
            return self.origin_datetime + delta
        
        
    def datetime_to_index(self, dt):
        
        """
        Gets the index corresponding to the specified date and time.
        
        The argument must be a single `datetime`.
        
        If the origin `datetime` of this signal is not known, this
        method returns `None`. Otherwise it returns the inverse of the
        `index_to_datetime` method.
        """
        
        if self.origin_datetime is None:
            return None
        else:
            delta = dt - self.origin_datetime
            return delta.total_seconds() * self.sample_rate
