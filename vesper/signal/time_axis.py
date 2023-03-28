"""Module containing class `TimeAxis`."""


from vesper.signal.increasing_linear_map import IncreasingLinearMap


'''
a.length                   # signal length in sample frames

a.frame_rate               # signal frame rate, in hertz
a.frame_period             # signal frame period, in seconds

a.sample_rate              # `a.frame_rate`
a.sample_period            # `a.frame_period`

a.index_to_time(i)         # `i` in [0, length], scalar or array, int or float
a.time_to_index(t)         # `t` can be scalar or array. Result is float
                           # Maybe offer rounded int result as an option?
                           
a.start_time               # seconds
a.end_time                 # seconds
      
a.get_span(i, j)           # `index_to_time[j] - index_to_time[i]`
a.span                     # `get_span(0, length - 1)`, or None if length zero
a.duration                 # `get_span(0, length)`, or zero if length zero

a.index_to_datetime(i)     # `i` can be scalar or array, int or float.
a.datetime_to_index(t)     # `t` can be scalar or array. Result is float.

a.start_datetime           # `datetime` at start index, `None` if unknown
a.end_datetime             # `datetime` at end index, `None` if unknown
'''


# A possible class hierarchy for axes:
#
# Axis
#     IndexedAxis
#         TimeAxis
#         ArrayAxis
#     AmplitudeAxis


# TODO: Implement datetime-awareness. Include new `start_datetime`
# initializer argument.

# TODO: Implement piecewise linearly increasing time axes. Include new,
# mutually exclusive `index_times` and `index_datetimes` initializer
# arguments that specify (via a dictionary or a sequence of pairs
# mapping from indices to times or datetimes.


class TimeAxis:
    
    """Signal time axis."""
    
    
    def __init__(self, length, frame_rate, start_time=0):
        
        if length < 0:
            raise ValueError('Signal length cannot be negative.')
        
        if frame_rate <= 0:
            raise ValueError('Signal frame rate must be positive.')
        
        self._length = length
        self._frame_rate = frame_rate
        self._index_to_time_map = \
            IncreasingLinearMap(1 / frame_rate, start_time)

        
    def __eq__(self, other):
        return isinstance(other, TimeAxis) and \
            self.length == other.length and \
            self.frame_rate == other.frame_rate
                   

    @property
    def length(self):

        """
        Axis length in sample frames.

        This class has this property instead of a `__len__` special
        method since a time axis is not itself a sequence. It only
        provides information about a sequence.
        """

        return self._length
               
        
    @property
    def frame_rate(self):
        return self._frame_rate
    
    
    @property
    def frame_period(self):
        return 1 / self.frame_rate
    
    
    @property
    def sample_rate(self):
        return self.frame_rate


    @property
    def sample_period(self):
        return self.frame_period

        
    def index_to_time(self, indices):
        return self._index_to_time_map(indices)
    
    
    def time_to_index(self, times):
        return self._index_to_time_map.inverse(times)
    
    
    @property
    def start_time(self):
        return self._index_to_time(0)
     
    
    def _index_to_time(self, index):
        if self.length == 0:
            return None
        else:
            return self.index_to_time(index)
    
    
    @property
    def end_time(self):
        return self._index_to_time(self.length - 1)
    
    
    def get_span(self, i, j):
        self._check_index(i)
        self._check_index(j)
        return self.index_to_time(j) - self.index_to_time(i)
    
    
    def _check_index(self, i):
        if i < 0 or i >= self.length:
            raise ValueError(
                f'Invalid index {i} for signal of length {self.length}.')


    @property
    def span(self):

        length = self.length

        if length == 0:
            return None
        else:
            return self.get_span(0, length - 1)


    @property
    def duration(self):
        
        span = self.span

        if span is None:
            return 0

        else:
            # signal not empty
 
            # We define the duration in terms of the span so the it
            # will behave well for nonlinear index to time mappings.
            return span + self.frame_period
    
    
#     def index_to_datetime(self, indices):
#         return self._datetime_convert(
#             indices, self._index_to_datetime, Number)
#         
#         
#     def _datetime_convert(self, data, method, type_):
#         
#         ref = self.reference_datetime
#         
#         if ref is not None:
#             
#             # Augment reference date/time with time at reference index.
#             # We do this every time this method is called to allow for
#             # mutable index to time mappings.
#             ref = Bunch(ref, time=self.index_to_time(ref.index))
#             
#         if isinstance(data, type_):
#             return method(data, ref)
#         else:
#             return [method(d, ref) for d in data]
#         
#         
#     def _index_to_datetime(self, index, ref):
#         
#         if ref is None:
#             return None
#         
#         else:
#             time = self.index_to_time(index)
#             delta = time - ref.time
#             td = datetime.timedelta(seconds=delta)
#             return ref.datetime + td
# 
# 
#     def datetime_to_index(self, datetimes):
#         return self._datetime_convert(
#             datetimes, self._datetime_to_index, datetime.datetime)
#         
#         
#     def _datetime_to_index(self, dt, ref):
#         
#         if ref is None:
#             return None
#         
#         else:
#             td = dt - ref.datetime
#             time = ref.time + td.total_seconds()
#             return self.time_to_index(time)
#     
#     
#     @property
#     def start_datetime(self):
#         return self.index_to_datetime(self.start_index)
# 
# 
#     @property
#     def end_datetime(self):
#         if self.end_time is None:
#             return None
#         else:
#             return self.index_to_datetime(self.end_index)
