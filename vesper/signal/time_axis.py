"""Module containing `TimeAxis` class."""


from numbers import Number
import datetime

from .axis import Axis
from .linear_mapping import LinearMapping


'''
a.sample_rate            # hertz
a.sample_period          # seconds (same as `index_step_size`)
a.duration               # length times sample period

a.start_time             # seconds
a.end_time               # seconds

a.start_datetime         # `datetime`
a.end_datetime           # `datetime`

a.index_to_time(indices)         # indices may be float
a.time_to_index(times)           # indices are float
a.index_to_datetime(indices)     # indices may be float
a.datetime_to_index(datetimes)   # indices are float
'''


class TimeAxis(Axis):
    
    
    def __init__(
            self, start_index=0, length=0, sample_rate=1, origin_time=0,
            origin_datetime=None):
        
        sample_period = 1 / sample_rate
        mapping = LinearMapping(sample_period, origin_time)
        
        super().__init__('Time', 'seconds', 'S', start_index, length, mapping)
        
        self._sample_rate = sample_rate
        self._origin_datetime = origin_datetime
        
    
    start_index = Axis.start_index
    length = Axis.length
    
    
    @start_index.setter
    def start_index(self, i):
        self._start_index = i
        
        
    @length.setter
    def length(self, n):
        self._length = n
        
    
    @property
    def sample_rate(self):
        return self._sample_rate
    
    
    @property
    def sample_period(self):
        return 1 / self.sample_rate
    
    
    @property
    def duration(self):
        return self.length * self.sample_period
    
    
    @property
    def origin_time(self):
        return self._index_to_value_mapping.b
    
    
    @property
    def origin_datetime(self):
        return self._origin_datetime
    
    
    start_time = Axis.start_value
    end_time = Axis.end_value
    
    
    @property
    def start_datetime(self):
        if self.start_time is None:
            return None
        else:
            return self.index_to_datetime(self.start_index)


    @property
    def end_datetime(self):
        if self.end_time is None:
            return None
        else:
            return self.index_to_datetime(self.end_index)
    
    
    index_to_time = Axis.index_to_value
    time_to_index = Axis.value_to_index
    
    
    def index_to_datetime(self, indices):
        
        if isinstance(indices, Number):
            return self._index_to_datetime(indices)
        
        else:
            return [self._index_to_datetime(i) for i in indices]
        
        
    def _index_to_datetime(self, index):
        
        if self._origin_datetime is None:
            return None
        
        else:
            time = self.index_to_time(index)
            seconds_from_origin = time - self.origin_time
            td = datetime.timedelta(seconds=seconds_from_origin)
            return self._origin_datetime + td


    def datetime_to_index(self, datetimes):
        
        if isinstance(datetimes, datetime.datetime):
            return self._datetime_to_index(datetimes)
        
        else:
            return [self._datetime_to_index(dt) for dt in datetimes]
        
        
    def _datetime_to_index(self, dt):
        
        if self._origin_datetime is None:
            return None
        
        else:
            td = dt - self._origin_datetime
            time = self.origin_time + td.total_seconds()
            return self.time_to_index(time)
