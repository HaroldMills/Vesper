"""Module containing `Schedule` class."""


from collections import namedtuple
import datetime
import itertools

import pytz
import yaml


Interval = namedtuple('Interval', ('start', 'end'))
Transition = namedtuple('Transition', ('datetime', 'state'))


class Schedule:
    
    """
    Sequence of UTC intervals.
    
    A `Schedule` is a sequence of UTC time intervals, interpreted as a
    function from UTC time to a boolean *state*. The schedule is `True`
    or *on* from the start of each interval up to but not including the
    end of the interval, and the schedule is `False` or *off* at all
    other times. A schedule can also be interpreted as a sequence of
    transitions, with a transition at each interval boundary from the
    state approaching the boundary to the state at the boundary.
    Transitions at the beginnings of intervals are from `False` to
    `True`, and transitions at the ends of intervals are from `True`
    to `False`.
    """
    
    
    MIN_DATETIME = pytz.utc.localize(datetime.datetime.min)
    MAX_DATETIME = pytz.utc.localize(datetime.datetime.max)
    
    
    @staticmethod
    def compile_yaml(spec, lat=None, lon=None, time_zone=None):
        
        try:
            spec = yaml.load(spec)
        except Exception as e:
            raise ValueError(
                'Could not load schedule YAML. Error message was: {}'.format(
                    e.message))
            
        return Schedule.compile_dict(spec, lat, lon, time_zone)
    
        
    @staticmethod
    def compile_dict(spec, lat=None, lon=None, time_zone=None):
        from vesper.schedule.schedule_compilers import compile_schedule
        context = {'lat': lat, 'lon': lon, 'time_zone': time_zone}
        return compile_schedule(spec, context)
    
    
    def __init__(self, intervals):
        self._intervals = _normalize(intervals)
        
        
    def get_intervals(self, start=None, end=None):
        
        """
        Returns an iterator for the intervals of this schedule that
        intersect the query interval [`start`, `end`]. For the purpose
        of determining intersection, the schedule intervals are
        considered to be closed at both ends.
        """
        
        start, end = _complete_query_interval(start, end)
            
        if start <= end:
            # query interval is not empty
            
            i = self._find_first_interval_with_end_ge(start)
            intervals = self._intervals
                        
            while i != len(intervals) and intervals[i].start <= end:
                yield intervals[i]
                i += 1
            
  
    def _find_first_interval_with_end_ge(self, dt):
        
        """
        Returns the index of the first interval of this schedule whose end
        is at least `dt`, or the number of intervals of the schedule if there
        is no such interval.
        """
        
        intervals = self._intervals
        
        if len(intervals) == 0 or dt > intervals[-1].end:
            # there is no interval of this schedule whose end is at least `dt`.
            
            return len(intervals)
        
        else:
            # there is an interval of this schedule whose end is at least `dt`.
            
            low = -1
            high = len(intervals) - 1
            
            # Invariant: index of first interval of this schedule whose
            # end is at least `dt` is in (`low`, `high`].
            
            while high != low + 1:
                
                mid = (low + high) // 2
                
                if dt > intervals[mid].end:
                    low = mid
                else:
                    high = mid
                    
            return high
        
        
    def get_transitions(self, start=None, end=None):
        
        """
        Returns an iterator for the transitions of this schedule that
        are in the query interval [`start`, `end`].
        """
        
        start, end = _complete_query_interval(start, end)

        for s, e in self.get_intervals(start, end):
             
            if s >= start:
                yield Transition(s, True)
                 
            if e <= end:
                yield Transition(e, False)
    
    
    def get_state(self, dt):
        
        i = self._find_first_interval_with_end_ge(dt)
        
        if i == len(self._intervals):
            return False
        else:
            return self._intervals[i].start <= dt
    
    
def _normalize(intervals):
    
    if len(intervals) <= 1:
        
        return tuple(intervals)
    
    else:
        # have at least two intervals
        
        # Sort intervals by start time.
        sorted_intervals = sorted(intervals, key=lambda i: i.start)
        
        normalized_intervals = []
        normalized_interval = sorted_intervals[0]
        
        for interval in itertools.islice(sorted_intervals, 1, None):
            
            if normalized_interval.end < interval.start:
                # `normalized_interval` and `interval` do not intersect
                
                normalized_intervals.append(normalized_interval)
                normalized_interval = interval
                
            else:
                # `normalized_interval` and `interval` intersect
                
                # Update end of `normalized_interval` if needed.
                if interval.end > normalized_interval.end:
                    normalized_interval = normalized_interval._replace(
                        end=interval.end)
                
        normalized_intervals.append(normalized_interval)
        
        return tuple(normalized_intervals)


def _complete_query_interval(start, end):

    if start is None:
        start = Schedule.MIN_DATETIME
            
    if end is None:
        end = Schedule.MAX_DATETIME
         
    return (start, end)
