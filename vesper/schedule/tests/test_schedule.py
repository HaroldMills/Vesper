import datetime
import itertools

import pytz

from vesper.schedule.schedule import Interval, Schedule, Transition
from vesper.tests.test_case import TestCase
import vesper.schedule.schedule as schedule


def _dt(hour, minute=0, second=0):
    dt = datetime.datetime(2016, 12, 2, hour, minute, second)
    return pytz.utc.localize(dt)


_INTERVALS = (
    Interval(_dt(1), _dt(2)),
    Interval(_dt(3), _dt(4)),
    Interval(_dt(5), _dt(6))
)

_SCHEDULE = Schedule(_INTERVALS)

_TRANSITIONS = tuple(itertools.chain(*(
    (Transition(i.start, True), Transition(i.end, False)) for i in _INTERVALS)))

def _get_intervals(*args, **kwargs):
    return tuple(_SCHEDULE.get_intervals(*args, **kwargs))

def _get_transitions(*args, **kwargs):
    return tuple(_SCHEDULE.get_transitions(*args, **kwargs))


class ScheduleTests(TestCase):
    
    
    def test_normalize(self):
        
        cases = (
            
            # no intervals
            (
                (),
                ()
            ),
            
            # one interval   
            (
                ((1, 2),),
                ((1, 2),)
            ),
                 
            # two disjoint intervals in order
            (
                ((1, 2), (3, 4)),
                ((1, 2), (3, 4))
            ),
                 
            # two disjoint intervals out of order
            (
                ((3, 4), (1, 2)),
                ((1, 2), (3, 4))
            ),
                 
            # two intersecting (barely) intervals out of order
            (
                ((2, 3), (1, 2)),
                ((1, 3),)
            ),
                  
            # two intersecting intervals out of order
            (
                ((2, 4), (1, 3)),
                ((1, 4),)
            ),
                 
            # two intersecting intervals, the second included in the first
            (
                ((1, 4), (2, 3)),
                ((1, 4),)
            ),
                 
            # multiple intersecting intervals
            (
                ((1, 2), (3, 9), (4, 5), (6, 7), (8, 10), (11, 12)),
                ((1, 2), (3, 10), (11, 12))
            ),
                 
            # multiple intersecting intervals, some out of order
            (
                ((11, 12), (6, 7), (1, 2), (8, 10), (3, 9), (4, 5)),
                ((1, 2), (3, 10), (11, 12))
            ),
            
            # more multiple intersecting intervals  
            (
                ((1, 3), (2, 3), (4, 5), (4, 6), (5, 7)),
                ((1, 3), (4, 7))
            )
               
        )
        
        for intervals, expected in cases:
            intervals = _dtize(intervals)
            expected = _dtize(expected)
            actual = schedule._normalize(intervals)
            self.assertEqual(actual, expected)

    
    
    def test_find_first_interval_with_end_ge(self):
        
        cases = (
            (_dt(0, 30), 0),
            (_dt(1), 0),
            (_dt(1, 30), 0),
            (_dt(2), 0),
            (_dt(2, 30), 1),
            (_dt(3), 1),
            (_dt(3, 30), 1),
            (_dt(4), 1),
            (_dt(4, 30), 2),
            (_dt(5), 2),
            (_dt(5, 30), 2),
            (_dt(6), 2),
            (_dt(6, 30), 3)
        )
        
        for dt, expected in cases:
            actual = _SCHEDULE._find_first_interval_with_end_ge(dt)
            self.assertEqual(actual, expected)
            
            
    def test_get_intervals(self):
          
        cases = (
             
            # query intervals that include all of schedule
            (None, None, _INTERVALS),
            (_dt(0), _dt(7), _INTERVALS),
            (_dt(1), _dt(6), _INTERVALS),
             
            # query interval that intersects all of schedule, but does
            # not include it
            (_dt(1, 30), _dt(5, 30), _INTERVALS),
              
            # query intervals that intersect part of schedule
            (_dt(3, 30), _dt(5, 30), _INTERVALS[1:]),
            (_dt(1, 30), _dt(3, 30), _INTERVALS[:-1]),
            (_dt(3), _dt(3), (_INTERVALS[1],)),
            (_dt(3, 30), _dt(3, 30), (_INTERVALS[1],)),
            (_dt(4), _dt(4), (_INTERVALS[1],)),
            (None, _dt(1, 30), (_INTERVALS[0],)),
            (_dt(5, 30), None, (_INTERVALS[-1],)),
              
            # query intervals that do not intersect schedule
            (None, _dt(0), ()),
            (_dt(0), _dt(0, 30), ()),
            (_dt(6, 30), _dt(7), ()),
            (_dt(7), None, ()),
              
            # empty query intervals
            (_dt(3, 30), _dt(3), ())
             
        )
         
        for start, end, expected in cases:
            actual = _get_intervals(start, end)
            self.assertEqual(actual, expected)
             
        # no query interval
        actual = _get_intervals()
        self.assertEqual(actual, _INTERVALS)
         
        # query start as positional arg
        actual = _get_intervals(_dt(3))
        self.assertEqual(actual, _INTERVALS[1:])
         
        # query start as keyword arg
        actual = _get_intervals(start=_dt(3))
        self.assertEqual(actual, _INTERVALS[1:])
         
        # query end as keyword arg
        actual = _get_intervals(end=_dt(4))
        self.assertEqual(actual, _INTERVALS[:2])
             
         
    def test_get_transitions(self):
         
        cases = (
             
            # query intervals that include all transitions
            (None, None, _TRANSITIONS),
            (_dt(0), _dt(7), _TRANSITIONS),
            (_dt(1), _dt(6), _TRANSITIONS),
            
            # query intervals that include only some transitions
            (None, _dt(1), (_TRANSITIONS[0],)),
            (_dt(0), _dt(2), _TRANSITIONS[:2]),
            (_dt(0), _dt(3, 30), _TRANSITIONS[:3]),
            (_dt(1, 30), _dt(5, 30), _TRANSITIONS[1:-1]),
            (_dt(5, 30), _dt(7), (_TRANSITIONS[-1],)),
            (_dt(1), _dt(1), (_TRANSITIONS[0],)),
            (_dt(6), _dt(6), (_TRANSITIONS[-1],)),
            (_dt(6), None, (_TRANSITIONS[-1],)),
            
            # query intervals that include no transitions
            (None, _dt(0), ()),
            (_dt(0), _dt(0, 30), ()),
            (_dt(0), _dt(0), ()),
            (_dt(1, 30), _dt(1, 40), ()),
            (_dt(1, 30), _dt(1, 30), ()),
            (_dt(7), None, ()),
            (_dt(7), _dt(8), ()),
            (_dt(7), _dt(7), ())
             
        )
         
        for start, end, expected in cases:
            actual = _get_transitions(start, end)
            self.assertEqual(actual, expected)
             
        # no query interval
        actual = _get_transitions()
        self.assertEqual(actual, _TRANSITIONS)
         
        # query start as positional arg
        actual = _get_transitions(_dt(3))
        self.assertEqual(actual, _TRANSITIONS[2:])
         
        # query start as keyword arg
        actual = _get_transitions(start=_dt(3))
        self.assertEqual(actual, _TRANSITIONS[2:])
         
        # query end as keyword arg
        actual = _get_transitions(end=_dt(4))
        self.assertEqual(actual, _TRANSITIONS[:4])

             
    def test_get_state(self):
         
        cases = (
            (_dt(0, 30), False),
            (_dt(1), True),
            (_dt(1, 30), True),
            (_dt(2), True),
            (_dt(2, 30), False),
            (_dt(3), True),
            (_dt(3, 30), True),
            (_dt(4), True),
            (_dt(4, 30), False),
            (_dt(5), True),
            (_dt(5, 30), True),
            (_dt(6), True),
            (_dt(6, 30), False)
        )
         
        for dt, expected in cases:
            actual = _SCHEDULE.get_state(dt)
            self.assertEqual(actual, expected)
        
        
def _dtize(intervals):
    return tuple(_dtize_interval(*i) for i in intervals)


def _dtize_interval(start, end):
    return Interval(_dt(start), _dt(end))


# _TIME_ZONE = pytz.timezone('US/Eastern')
# _LAT = 42.5
# _LON = -76.5
# 
# _START_DATE = datetime.datetime(2016, 7, 15)
# _END_DATE = datetime.datetime(2016, 7, 17)
#         

# def _dt(year, month, day, hour):
#     return datetime.datetime(year, month, day, hour, tzinfo=pytz.utc)
# 
# 
# class DailyIntervalTests(TestCase):
#     
#     
#     def test_daily_interval(self):
#         
#         s = DailyInterval(
#             datetime.time(6), datetime.time(18), _START_DATE, _END_DATE,
#             time_zone=_TIME_ZONE)
#         
#         for i, actual in enumerate(s.intervals()):
#             expected = (_dt(2016, 7, 15 + i, 10), _dt(2016, 7, 15 + i, 22))
#             self.assertEqual(actual, expected)
#             
#             
#     def test_nightly_interval(self):
#         
#         s = DailyInterval(
#             datetime.time(18), datetime.time(6), _START_DATE, _END_DATE,
#             time_zone=_TIME_ZONE)
# 
#         for i, actual in enumerate(s.intervals()):
#             expected = (_dt(2016, 7, 15 + i, 22), _dt(2016, 7, 16 + i, 10))
#             self.assertEqual(actual, expected)
# 
# 
#     def test_daily_solar_interval(self):
#         
#         # These times are from a USNO table for the above latitude and
#         # longitude and the UTC-04:00 time zone (i.e. EDT).
#         expected_intervals = (
#             ((2016, 7, 15, 5, 43), (2016, 7, 15, 20, 41)),
#             ((2016, 7, 16, 5, 43), (2016, 7, 16, 20, 40)),
#             ((2016, 7, 17, 5, 44), (2016, 7, 17, 20, 40))
#         )
#         
#         s = DailyInterval(
#             SolarEventTime('Sunrise'), SolarEventTime('Sunset'),
#             _START_DATE, _END_DATE, lat=_LAT, lon=_LON)
#         
#         for i, interval in enumerate(s.intervals()):
#             self._assert_intervals_almost_equal(interval, expected_intervals[i])
# 
#     
#     def test_nightly_solar_interval(self):
#          
#         # These times are from a USNO table for the above latitude and
#         # longitude and the UTC-04:00 time zone (i.e. EDT).
#         expected_intervals = (
#             ((2016, 7, 15, 20, 41), (2016, 7, 16, 5, 43)),
#             ((2016, 7, 16, 20, 40), (2016, 7, 17, 5, 44)),
#             ((2016, 7, 17, 20, 40), (2016, 7, 18, 5, 45))
#         )
#         
#         s = DailyInterval(
#             SolarEventTime('Sunset'), SolarEventTime('Sunrise'),
#             _START_DATE, _END_DATE, lat=_LAT, lon=_LON)
#         
#         for i, interval in enumerate(s.intervals()):
#             self._assert_intervals_almost_equal(interval, expected_intervals[i])
#             
#             
#     def _assert_intervals_almost_equal(self, actual, expected):
#         
#         actual_start, actual_end = actual
#         actual_start = _round(actual_start)
#         actual_end = _round(actual_end)
#         
#         expected_start, expected_end = expected
#         expected_start = _to_utc(expected_start)
#         expected_end = _to_utc(expected_end)
#         
#         self._assert_datetimes_almost_equal(actual_start, expected_start)
#         self._assert_datetimes_almost_equal(actual_end, expected_end)
# 
# 
#     def _assert_datetimes_almost_equal(self, a, b):
#         diff = (a - b).total_seconds()
#         self.assertLessEqual(diff, 60)
#         
#         
# def _round(dt):
#     return time_utils.round_datetime(dt, 60)
# 
# 
# def _to_utc(dt):
#     dt = datetime.datetime(*dt)
#     dt += datetime.timedelta(hours=4)
#     return pytz.utc.localize(dt)
