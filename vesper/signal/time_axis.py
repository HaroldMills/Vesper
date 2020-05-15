"""Module containing class `TimeAxis`."""


from vesper.signal.linear_map import LinearMap


'''
a.start_index
a.end_index
a.length                   # signal length in sample frames

a.frame_rate               # signal frame rate, in hertz
a.frame_period             # signal frame period, in seconds

a.offset                   # index to time offset, in seconds

a.index_to_time(i)         # `i` in [0, length], scalar or array, int or float
a.time_to_index(t)         # `t` can be scalar or array. Result is float
                           # Maybe offer rounded int result as an option?
                           
a.start_time
a.end_time
      
a.get_span(i, j)           # `index_to_time[j] - index_to_time[i]`
a.span                     # `get_span(0, length - 1)`, or None if length zero
a.duration                 # `get_span(0, length)`, or zero if length zero

a.index_to_datetime(i)     # `i` can be scalar or array, int or float.
a.datetime_to_index(t)     # `t` can be scalar or array. Result is float.

a.start_datetime           # `datetime` at start index, `None` if unknown
a.end_datetime             # `datetime` at end index, `None` if unknown
'''


# TODO: Add support for datetime-aware and piecewise linear (as opposed
# to just plain linear) time axes. Common use cases will be:
#
#     1. Knowing the start datetime of a linear time axis, e.g.
#        the start datetime of an audio file.
#
#     2. Knowing several (index, datetime) pairs, e.g. the start
#        datetimes of the files of an audio file sequence.
#
# To support these cases, one might add an `index_datetimes` initializer
# argument that is a dictionary mapping time axis indices to datetimes.
# However, that by itself would not support the specification a nonlinear
# time axis that is not datetime-aware. A remedy might be to include an
# additional `index_times` initializer argument that is a dictionary
# mapping time axis indices to times. Then one could provide one or the
# other of these arguments (but not both) to create a nonlinear time axis,
# either datetime-aware or not. Specifying an `index_datetimes` dictionary
# containing a single item would create a linear datetime-aware time axis.


class TimeAxis:
    
    """Signal time axis."""
    
    
    def __init__(self, length, frame_rate, offset=0):
        
        if length < 0:
            raise ValueError('Time axis length cannot be negative.')
        
        if frame_rate <= 0:
            raise ValueError('Time axis frame rate must be positive.')
        
        self._length = length
        self._frame_rate = frame_rate
        self._offset = offset
 
        self._index_to_time_map = LinearMap(1 / frame_rate, offset)

        
    def __eq__(self, other):
        return isinstance(other, TimeAxis) and \
            self.length == other.length and \
            self.frame_rate == other.frame_rate
                   

    @property
    def start_index(self):
        if self.length == 0:
            return None
        else:
            return 0
        
        
    @property
    def end_index(self):
        length = self.length
        if length == 0:
            return None
        else:
            return length - 1
        
        
    @property
    def length(self):
        return self._length
               
        
    @property
    def frame_rate(self):
        return self._frame_rate
    
    
    @property
    def frame_period(self):
        return 1 / self.frame_rate
    
    
    @property
    def offset(self):
        return self._offset
    
    
    def index_to_time(self, indices):
        return self._index_to_time_map(indices)
    
    
    def time_to_index(self, times):
        return self._index_to_time_map.inverse(times)
    
    
    @property
    def start_time(self):
        return self._index_to_time(self.start_index)
    
    
    def _index_to_time(self, index):
        if index is None:
            return None
        else:
            return self.index_to_time(index)
    
    
    @property
    def end_time(self):
        return self._index_to_time(self.end_index)
    
    
    def get_span(self, i, j):
        return self.index_to_time(j) - self.index_to_time(i)
    
    
    @property
    def span(self):
        if self.length == 0:
            return None
        else:
            return self.get_span(self.start_index, self.end_index)


    @property
    def duration(self):
        
        if self.length == 0:
            return 0
        
        else:
            
            # We define the duration in terms of the span so the it
            # will behave well for nonlinear index to time mappings.
            return self.span + self.frame_period
    
    
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
