"""Module containing `TimeAxis` class."""


from numbers import Number
import datetime

from vesper.signal.indexed_axis import IndexedAxis
from vesper.signal.linear_mapping import LinearMapping
from vesper.util.bunch import Bunch


'''
a.name                   # e.g. 'Time', 'Frequency'
a.units                  # `Bunch` with `plural`, `singular`, and
                         # `abbreviation` attributes

a.start_index            # start of index range
a.end_index              # end of index range, `None` if length zero
a.length                 # axis length in indices

a.sample_rate            # hertz
a.sample_period          # seconds (same as `index_step_size`)

a.index_to_time_mapping
a.index_to_time(i)       # indices may be float
a.time_to_index(t)       # indices are float

a.start_time             # time at start index, `None` if length zero
a.end_time               # time at end index, `None` if length zero
a.span                   # end time less start time, `None` if length zero
a.duration               # span plus sample period, zero if length zero

a.reference_datetime     # `Bunch` with `index` and `datetime` attributes
a.index_to_datetime(i)   # indices may be float
a.datetime_to_index(dt)  # indices are float

a.start_datetime         # `datetime` at start index, `None` if unknown
a.end_datetime           # `datetime` at start index, `None` if unknown
'''


_NAME = 'Time'
_UNITS = Bunch(plural='seconds', singular='second', abbreviation='S')


class TimeAxis(IndexedAxis):
    
    
    def __init__(
            self, start_index=0, length=0, sample_rate=1,
            index_to_time_mapping=None, reference_datetime=None):
        
        super().__init__(_NAME, _UNITS, start_index, length)
        
        self._sample_rate = sample_rate
        
        self._index_to_time_mapping = self._get_index_to_time_mapping(
            index_to_time_mapping, sample_rate)
            
        self.reference_datetime = reference_datetime
        
    
    def _get_index_to_time_mapping(self, index_to_time_mapping, sample_rate):
        if index_to_time_mapping is None:
            return LinearMapping(1 / sample_rate)
        else:
            return index_to_time_mapping

        
    def __eq__(self, other):
        return isinstance(other, TimeAxis) and \
            IndexedAxis.__eq__(self, other) and \
            self.sample_rate == other.sample_rate and \
            self.index_to_time_mapping == other.index_to_time_mapping and \
            self.reference_datetime == other.reference_datetime
                   

    start_index = IndexedAxis.start_index
    
    
    @start_index.setter
    def start_index(self, i):
        self._start_index = i
        
        
    length = IndexedAxis.length

    
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
    def index_to_time_mapping(self):
        return self._index_to_time_mapping
    
    
    def index_to_time(self, indices):
        return self._index_to_time_mapping.map(indices)
    
    
    def time_to_index(self, times):
        return self._index_to_time_mapping.invert(times)
    
    
    @property
    def start_time(self):
        return self.index_to_time(self.start_index)
    
    
    @property
    def end_time(self):
        if self.length == 0:
            return None
        else:
            return self.index_to_time(self.end_index)
    
    
    @property
    def span(self):
        if self.length == 0:
            return None
        else:
            return self.end_time - self.start_time


    @property
    def duration(self):
        
        if self.length == 0:
            return 0
        
        else:
            
            # We define the duration in terms of the span so the it
            # will behave well for nonlinear index to time mappings.
            return self.span + self.sample_period
    
    
    @property
    def reference_datetime(self):
        return self._reference_datetime
    
    
    @reference_datetime.setter
    def reference_datetime(self, reference_datetime):
        if reference_datetime is None:
            self._reference_datetime = None
        else:
            self._reference_datetime = Bunch(reference_datetime)
        
        
    def index_to_datetime(self, indices):
        return self._datetime_convert(indices, self._index_to_datetime, Number)
        
        
    def _datetime_convert(self, data, method, type_):
        
        ref = self.reference_datetime
        
        if ref is not None:
            
            # Augment reference date/time with time at reference index.
            # We do this every time this method is called to allow for
            # mutable index to time mappings.
            ref = Bunch(ref, time=self.index_to_time(ref.index))
            
        if isinstance(data, type_):
            return method(data, ref)
        else:
            return [method(d, ref) for d in data]
        
        
    def _index_to_datetime(self, index, ref):
        
        if ref is None:
            return None
        
        else:
            time = self.index_to_time(index)
            delta = time - ref.time
            td = datetime.timedelta(seconds=delta)
            return ref.datetime + td


    def datetime_to_index(self, datetimes):
        return self._datetime_convert(
            datetimes, self._datetime_to_index, datetime.datetime)
        
        
    def _datetime_to_index(self, dt, ref):
        
        if ref is None:
            return None
        
        else:
            td = dt - ref.datetime
            time = ref.time + td.total_seconds()
            return self.time_to_index(time)
    
    
    @property
    def start_datetime(self):
        return self.index_to_datetime(self.start_index)


    @property
    def end_datetime(self):
        if self.end_time is None:
            return None
        else:
            return self.index_to_datetime(self.end_index)
