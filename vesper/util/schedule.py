"""Module containing `Schedule` class."""


from collections import namedtuple
from datetime import (
    date as Date,
    datetime as DateTime,
    time as Time,
    timedelta as TimeDelta)
from threading import Event, Thread
import itertools
import re

import jsonschema
import pytz

from vesper.ephem.sun_moon import SunMoon
from vesper.util.notifier import Notifier
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Consider creating a separate interval module, including intersection
# functions.


Interval = namedtuple('Interval', ('start', 'end'))
Transition = namedtuple('Transition', ('time', 'state'))


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
    
    
    MIN_DATETIME = pytz.utc.localize(DateTime.min)
    MAX_DATETIME = pytz.utc.localize(DateTime.max)
    
    
    # The `latitude`, `longitude`, and `time_zone` arguments to
    # `compile_yaml` and `compile_dict` are separate rather than
    # collected into an object since for many purposes (namely,
    # those that involve schedules that specify local times but
    # no twilight events like sunrise or sunset) the time zone is
    # needed but not the latitude and longitude.
    
    
    @staticmethod
    def compile_yaml(spec, latitude=None, longitude=None, time_zone=None):
        
        try:
            spec = yaml_utils.load(spec)
        except Exception as e:
            raise ValueError(
                'Could not load schedule YAML. Error message was: {}'.format(
                    e.message))
            
        return Schedule.compile_dict(spec, latitude, longitude, time_zone)
    
        
    @staticmethod
    def compile_dict(spec, latitude=None, longitude=None, time_zone=None):
        location = _Location(latitude, longitude, time_zone)
        return _compile_schedule(spec, location)
    
    
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


class ScheduleRunner(Thread):
    
    
    def __init__(self, schedule):
        super().__init__(daemon=True)
        self._schedule = schedule
        self._notifier = Notifier(schedule)
        self._stop_event = Event()
        self._terminated_event = Event()
            
        
    def add_listener(self, listener):
        self._notifier.add_listener(listener)
    
    
    def remove_listener(self, listener):
        self._notiier.remove_listener(listener)
    
    
    def clear_listeners(self):
        self._notifier.clear_listeners()
    
    
    def run(self):
        
        schedule = self._schedule
        stop_event = self._stop_event
        terminated_event = self._terminated_event
        notify = self._notifier.notify_listeners
        
        now = time_utils.get_utc_now()
        state = schedule.get_state(now)
        notify('schedule_run_started', now, state)
        
        transitions = tuple(schedule.get_transitions(start=now))
        
        for i, t in enumerate(transitions):
            
            self._wait_for_transition_or_stop(t)
            
            if stop_event.is_set():
                # stop requested
                
                # Because there are multiple threads at play, it is
                # possible (though unlikely) that `now` follows or
                # equals the times of one or more transitions in
                # `transitions[i:]`, i.e. that the transitions have
                # occurred but the schedule's listeners have not been
                # notified of them. We perform the notifications here.
                while i < len(transitions) and transitions[i].time <= now:
                    t = transitions[i]
                    notify('schedule_state_changed', t.time, t.state)
                    i += 1
                    
                now = time_utils.get_utc_now()
                state = schedule.get_state(now)
                notify('schedule_run_stopped', now, state)
                
                terminated_event.set()
                
                return
            
            else:
                notify('schedule_state_changed', t.time, t.state)
                    
        # If we get here, the schedule run completed. The schedule is off
        # since we are at or past the end of every interval of the schedule.
        
        now = time_utils.get_utc_now()
        notify('schedule_run_completed', now, False)
                
        terminated_event.set()
        
        
    def _wait_for_transition_or_stop(self, t):
        
        while True:
            
            now = time_utils.get_utc_now()
            seconds = (t.time - now).total_seconds()
            
            if seconds <= 0:
                # transition time reached
                
                return
            
            else:
                # transition time not reached
                
                # We limit the wait duration to avoid `OverflowError`
                # exceptions that we have seen (admittedly for very
                # large numbers of seconds) if we don't. We keep the
                # maximum wait duration fairly small on the hunch that
                # doing so might improve the accuracy of schedule
                # transition notification times, at least on some
                # platforms.
                seconds = min(seconds, 5)
                self._stop_event.wait(seconds)
                
                if self._stop_event.is_set():
                    return
            
            
    def stop(self):
        self._stop_event.set()
        
        
    def wait(self, timeout=None):
        self._terminated_event.wait(timeout)


class ScheduleListener:
    
    
    def schedule_run_started(self, schedule, time, state):
        pass
    
    
    def schedule_state_changed(self, schedule, time, state):
        pass
    
    
    def schedule_run_stopped(self, schedule, time, state):
        pass
    
    
    def schedule_run_completed(self, schedule, time, state):
        pass


# The functions below compile schedules from dictionary schedule
# specifications to `Schedule` objects. There are two sets of functions
# involved, the *parse* functions and the *compile* functions. The parse
# functions parse schedule dates and/or times from strings, while the
# compile functions compile dictionary schedule specifications into
# `Schedule` objects. The parse functions are lower-level than the
# compile functions, and are invoked by them.
 

'''
Grammar for schedule dates and times:

date ::= yyyy-mm-dd

time ::= nonoffset_time | offset_time

nonoffset_time ::= time_24 | am_pm_time | time_name | twilight_event_name

time_24 ::= h?h:mm:ss (with hour in [0, 23])
am_pm_time ::=  time_12 am_pm
time_12 ::= h?h:mm:ss | h?h:mm | h?h (with hour in [1, 12])
am_pm ::= 'am' | 'pm'
time_name ::= 'noon' | 'midnight'
twilight_event_name = 'sunrise' | 'sunset' | 'civil dawn' | 'civil dusk' |
    'nautical dawn' | 'nautical dusk' | 'astronomical dawn' |
    'astronomical dusk'
    
offset_time ::= offset preposition twilight_event_name
offset ::= hhmmss_offset | units_offset
hhmmss_offset ::= h?h:mm:ss
units_offset ::= number units (with number 1 if units singular)
number ::= d+ | d+.d* | .d+
units ::= 'hours' | 'hour' | 'minutes' | 'minute' | 'seconds' | 'second'
preposition = 'before' | 'after'

date_time ::= date time


Time examples:
    12:34:56
    12 pm
    3:45 am
    noon
    midnight
    sunrise, sunset, etc.
    1:00:00 before sunset
    1 hour after sunset
    2 hours after sunset
    30 minutes after civil dusk
    10 seconds before nautical dawn
    
    
Date/time examples:
    2016-11-28 12:34:56
    2016-11-28 12 pm
    2016-11-28 noon
    2016-11-28 sunset
    2016-11-18 1 hour after sunset


Example schedules:

    interval:
        start: 2016-07-15 1 hour after sunset
        end: 2016-07-16 30 minutes before sunrise
        
    intervals:
        - start: 2016-07-15 noon
          duration: 1 hour
        - start: 2016-07-15 2 pm
          duration: 1 hour
          
    daily:
        start_time: 1 hour before sunrise
        end_time: 2 hours after sunrise
        start_date: 2016-07-15
        end_date: 2016-10-15
        
    union:
        - intervals
          ...
        - daily
          ...
         
          
Ideas not yet implemented:

    Periodic interval schedules:
        periodic:
            duration: 10 minutes
            period: 1 hour
            start_date_time: 2016-07-15 noon
            end_date_time: 2016-07-15 4 pm
        
    Day of week/month filtering in daily schedules, such as:
        days: [Monday, Wednesday, Friday]
        days: [Monday 1, Monday 3]
        days: [1, 15]
        
    Periodic schedules nested within daily schedules:
        daily:
            start_time: sunset
            end_time: sunrise
            periodic:
                duration: 10 minutes
                period: 1 hour
            start_date: 2016-07-15
            end_date: 2016-07-20
            
    Filtering of one schedule by another, including intersection.
    
    Schedule complementation.
            
            
See Simplenote entry "Recording Schedules, Take 2" for more information
about schedules.
'''


_INTERVAL_SCHEMA = yaml_utils.load('''
    type: object
    properties:
        interval:
            type: object
            properties:
                start: {}
                end: {}
                duration: {type: string}
            additionalProperties: false
    required: [interval]
    additionalProperties: false
''')


_INTERVALS_SCHEMA = yaml_utils.load('''
    type: object
    properties:
        intervals:
            type: array
            items:
                type: object
                properties:
                    start: {}
                    end: {}
                    duration: {type: string}
                additionalProperties: false
    required: [intervals]
    additionalProperties: false
''')


_DAILY_SCHEMA = yaml_utils.load('''
    type: object
    properties:
        daily:
            type: object
            properties:
                start_time: {type: string}
                end_time: {type: string}
                duration: {type: string}
                time_intervals:
                    type: array
                    items:
                        type: object
                        properties:
                            start: {type: string}
                            end: {type: string}
                            duration: {type: string}
                        additionalProperties: false
                start_date: {}
                end_date: {}
                date_intervals:
                    type: array
                    items:
                        type: object
                        properties:
                            start: {}
                            end: {}
                        required: [start, end]
                        additionalProperties: false
            additionalProperties: false
    required: [daily]
    additionalProperties: false
''')


_UNION_SCHEMA = yaml_utils.load('''
    type: object
    properties:
        union:
            type: array
            items:
                type: object
    required: [union]
    additionalProperties: false
''')


_INTERVAL_PROPERTY_NAMES = ('start', 'end', 'duration')
_RESTRICTED_INTERVAL_PROPERTY_NAMES = ('start', 'end')
_TIME_INTERVAL_PROPERTY_NAMES = ('start_time', 'end_time', 'duration')
_DATE_INTERVAL_PROPERTY_NAMES = ('start_date', 'end_date')

_ONE_DAY = TimeDelta(days=1)


def _compile_schedule(spec, location):
    
    for compile_ in _SCHEDULE_COMPILER_FUNCTIONS:
        schedule = compile_(spec, location)
        if schedule is not None:
            return schedule
            
    raise ValueError('Schedule specification was not of a recognized type.')


def _compile_interval_schedule(spec, location):
    
    try:
        interval = spec['interval']
    except KeyError:
        return None
    
    try:
        _check_spec_against_schema(spec, _INTERVAL_SCHEMA)
        interval = _compile_interval(interval, location)
    except ValueError as e:
        raise ValueError('Bad interval schedule: {}'.format(str(e)))
    
    return Schedule([interval])
    
    
def _check_spec_against_schema(spec, schema):
    try:
        jsonschema.validate(spec, schema)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(e.message)
    
        
def _compile_interval(interval, location):
    
    start = interval.get('start')
    end = interval.get('end')
    duration = interval.get('duration')
    
    _check_interval_properties_count(start, end, duration)
        
    if start is None:
        end = _compile_date_time(end, location, 'end')
        duration = _compile_duration(duration)
        return Interval(end - duration, end)
        
    elif end is None:
        start = _compile_date_time(start, location, 'start')
        duration = _compile_duration(duration)
        return Interval(start, start + duration)
    
    else:
        start = _compile_date_time(start, location, 'start')
        end = _compile_date_time(end, location, 'end')
        return Interval(start, end)
    
    
def _check_interval_properties_count(start, end, duration):
    if _count_non_nones(start, end, duration) != 2:
        raise ValueError(
            'Exactly two of the "start", "end", and "duration" properties '
            'must be specified.')


def _count_non_nones(*args):
    count = 0
    for arg in args:
        if arg is not None:
            count += 1
    return count
    
    
def _compile_date_time(dt, location, dt_name):
    
    if isinstance(dt, DateTime):
        return _naive_to_utc(dt, location, dt_name)
    
    elif isinstance(dt, str):
        
        dt_text = dt
        dt = _parse_date_time(dt)
        
        if dt is None:
            raise ValueError('Bad interval {} "{}".'.format(dt_name, dt_text))
        
        if isinstance(dt, DateTime):
            return _naive_to_utc(dt, location, dt_name, dt_text)
            
        else:
            _check_location_attribute(
                location.latitude, 'latitude', dt_name, dt_text)
            _check_location_attribute(
                location.longitude, 'longitude', dt_name, dt_text)
            return dt.resolve(location)
        
    else:
        raise ValueError(
            'Bad interval {} {}.'.format(dt_name, str(dt)))
        
    
def _naive_to_utc(dt, location, dt_name, dt_text=None):
    _check_location_attribute(
        location.time_zone, 'time zone', dt_name, dt_text)
    localized_dt = location.time_zone.localize(dt)
    return localized_dt.astimezone(pytz.utc)
    

def _check_location_attribute(value, name, dt_name, dt_text=None):
    
    if value is None:
        
        if dt_text is None:
            suffix = ''
        else:
            suffix = ' "{}"'.format(dt_text)
            
        raise ValueError(
            'No {} available to resolve interval {}{}.'.format(
                name, dt_name, suffix))


def _compile_duration(duration):
    try:
        return _parse_duration(duration.split())
    except Exception:
        raise ValueError('Bad interval duration "{}".'.format(duration))
    
    
def _compile_intervals_schedule(spec, location):
    
    try:
        intervals = spec['intervals']
    except KeyError:
        return None
    
    try:
        _check_spec_against_schema(spec, _INTERVALS_SCHEMA)
        intervals = tuple(_compile_interval(i, location) for i in intervals)
    except ValueError as e:
        raise ValueError('Bad intervals schedule: {}'.format(str(e)))
    
    return Schedule(intervals)

    
def _compile_daily_schedule(spec, location):
    
    try:
        daily = spec['daily']
    except KeyError:
        return None

    try:
        _check_daily_properties(spec)
        dates = _compile_daily_dates(daily)
        time_intervals = _compile_daily_time_intervals(daily)
        intervals = _compile_daily_intervals(dates, time_intervals, location)
    except ValueError as e:
        raise ValueError('Bad daily schedule: {}'.format(str(e)))
    
    return Schedule(intervals)


def _check_daily_properties(spec):
    _check_spec_against_schema(spec, _DAILY_SCHEMA)
    daily = spec['daily']
    _check_daily_date_interval_properties(daily)
    _check_daily_time_interval_properties(daily)
    
    
def _check_daily_date_interval_properties(spec):
    
    if 'date_intervals' in spec:
        
        _check_absence(spec, _DATE_INTERVAL_PROPERTY_NAMES, 'date_intervals')
        
        for interval in spec['date_intervals']:
            _check_presence(
                interval, _RESTRICTED_INTERVAL_PROPERTY_NAMES, 'date interval')
            
    elif _any_absent(spec, _DATE_INTERVAL_PROPERTY_NAMES):
        
        raise ValueError(
            'Schedule must include either "date_intervals" '
            'property or "start_date" and "end_date" properties.')
        
    
def _check_absence(spec, property_names, excluding_property_name):
    for name in property_names:
        if name in spec:
            raise ValueError(
                'Schedule cannot include both "{}" and "{}".'.format(
                    excluding_property_name, name))
            
            
def _check_presence(spec, property_names, spec_name):
    for name in property_names:
        if name not in spec:
            raise ValueError(
                '{} must include "{}" property.'.format(
                    spec_name.capitalize(), name))

            
def _any_absent(spec, property_names):
    for name in property_names:
        if name not in spec:
            return True
    return False


def _compile_daily_dates(spec):
    
    if 'date_intervals' in spec:
        date_intervals = _compile_date_intervals(spec['date_intervals'])
        date_iterator = itertools.chain.from_iterable(
            _get_dates(i) for i in date_intervals)
        unique_dates = set(date_iterator)
        return sorted(unique_dates)
        
    else:
        date_interval = \
            _compile_date_interval(spec, _DATE_INTERVAL_PROPERTY_NAMES)
        return tuple(_get_dates(date_interval))
        

def _compile_date_intervals(intervals):
    return tuple(
        _compile_date_interval(i, _RESTRICTED_INTERVAL_PROPERTY_NAMES)
        for i in intervals)


def _compile_date_interval(interval, property_names):
    start_name, end_name = property_names
    start = _compile_date(interval[start_name], 'start')
    end = _compile_date(interval[end_name], 'end')
    return (start, end)
    
    
def _get_dates(interval):
    date, end = interval
    while date <= end:
        yield date
        date += _ONE_DAY
        
        
def _compile_date(date, name):
    if isinstance(date, Date):
        return date
    else:
        if isinstance(date, str):
            suffix = '"{}"'.format(date)
        else:
            suffix = '{}'.format(str(date))
        raise ValueError('Bad {} date {}.'.format(name, suffix))
    
    
def _check_daily_time_interval_properties(spec):
    
    if 'time_intervals' in spec:
        
        _check_absence(spec, _TIME_INTERVAL_PROPERTY_NAMES, 'time_intervals')
        
        for interval in spec['time_intervals']:

            count = _count_properties(interval, _INTERVAL_PROPERTY_NAMES)
            
            if count != 2:
                
                raise ValueError(
                    'Time interval must include exactly two of the '
                    '"{}", "{}", and "{}" properties.'.format(
                        *_INTERVAL_PROPERTY_NAMES))
            
    else:
        
        count = _count_properties(spec, _TIME_INTERVAL_PROPERTY_NAMES)
        
        if count != 2:
            
            raise ValueError(
                'Schedule must include either "time_intervals" '
                'property or exactly two of the "{}", "{}", and "{}" '
                'properties.'.format(*_TIME_INTERVAL_PROPERTY_NAMES))
        
    
def _count_properties(spec, property_names):
    return len([name for name in property_names if name in spec])
               

def _compile_daily_time_intervals(spec):
     
    if 'time_intervals' in spec:
        return [
            _compile_time_interval(i, _INTERVAL_PROPERTY_NAMES)
            for i in spec['time_intervals']]
     
    else:
        return [_compile_time_interval(spec, _TIME_INTERVAL_PROPERTY_NAMES)]
         
         
def _compile_time_interval(spec, property_names):
     
    start_name, end_name, duration_name = property_names
     
    start = spec.get(start_name)
    end = spec.get(end_name)
    duration = spec.get(duration_name)
     
    if start is None:
        end = _compile_time(end, 'end')
        duration = _compile_duration(duration)
        return {'end': end, 'duration': duration}
         
    elif end is None:
        start = _compile_time(start, 'start')
        duration = _compile_duration(duration)
        return {'start': start, 'duration': duration}
     
    else:
        start = _compile_time(start, 'start')
        end = _compile_time(end, 'end')
        return {'start': start, 'end': end}
     
     
def _compile_time(time, name):
    result = _parse_time(time)
    if result is None:
        raise ValueError('Bad interval {} time "{}".'.format(name, time))
    return result


def _compile_daily_intervals(dates, time_intervals, location):
    return tuple(_compile_daily_intervals_aux(dates, time_intervals, location))


def _compile_daily_intervals_aux(dates, time_intervals, location):
    
    combine = _combine_date_and_time
    
    for date in dates:
        
        for interval in time_intervals:
            
            if 'start' not in interval:
                end = combine(date, interval['end'], location, 'end')
                duration = interval['duration']
                yield Interval(end - duration, end)
                
            elif 'end' not in interval:
                start = combine(date, interval['start'], location, 'start')
                duration = interval['duration']
                yield Interval(start, start + duration)
                
            else:
                start = combine(date, interval['start'], location, 'start')
                end = _get_daily_interval_end(start, interval['end'], location)
                yield Interval(start, end)
            
            
def _combine_date_and_time(date, time, location, name):
    
    if isinstance(time, Time):
        _check_location_attribute(location.time_zone, 'time zone', name)
        naive_dt = DateTime.combine(date, time)
        localized_dt = location.time_zone.localize(naive_dt)
        return localized_dt.astimezone(pytz.utc)
        
    else:
        _check_location_attribute(location.latitude, 'latitude', name)
        _check_location_attribute(location.longitude, 'longitude', name)
        dt = _TwilightEventDateTime(date, time.event_name, time.offset)
        return dt.resolve(location)


def _get_daily_interval_end(start, end_time, location):
    
    combine = _combine_date_and_time
    date = start.date()
    
    end = combine(date, end_time, location, 'end')
    
    if end < start:
        # end time will be on date following start time
        
        end = combine(date + _ONE_DAY, end_time, location, 'end')
        
    return end
        

def _compile_union_schedule(spec, location):
    
    try:
        union = spec['union']
    except KeyError:
        return None

    try:
        _check_spec_against_schema(spec, _UNION_SCHEMA)
    except ValueError as e:
        raise ValueError('Bad union schedule: {}'.format(str(e)))
    
    schedules = tuple(_compile_schedule(s, location) for s in union)
    intervals = tuple(itertools.chain.from_iterable(
        s.get_intervals() for s in schedules))
    
    return Schedule(intervals)


_SCHEDULE_COMPILER_FUNCTIONS = (
    _compile_interval_schedule,
    _compile_intervals_schedule,
    _compile_daily_schedule,
    _compile_union_schedule
)


class _Location:
    
    def __init__(self, latitude=None, longitude=None, time_zone=None):
        
        self.latitude = latitude
        self.longitude = longitude
        
        if isinstance(time_zone, str):
            self.time_zone = pytz.timezone(time_zone)
        else:
            self.time_zone = time_zone
            
        
_HHMMSS = re.compile(r'(\d?\d):(\d\d):(\d\d)')
_HHMM = re.compile(r'(\d?\d):(\d\d)')
_HH = re.compile(r'(\d?\d)')

_AM_PM = frozenset(('am', 'pm', 'AM', 'PM'))

_NAMED_TIMES = {
    'noon': Time(12),
    'midnight': Time(0)
}

_TWILIGHT_EVENT_NAMES = frozenset((
    'sunrise', 'sunset', 'civil dawn', 'civil dusk', 'nautical dawn',
    'nautical dusk', 'astronomical dawn', 'astronomical dusk'))

_INTEGER = re.compile(r'\d+')
_DECIMAL_1 = re.compile(r'\d+\.\d*')
_DECIMAL_2 = re.compile(r'\.\d+')
_NUMBER_RES = (_INTEGER, _DECIMAL_1, _DECIMAL_2)

_UNITS_FACTORS = {
    'hours': 3600,
    'hour': 3600,
    'minutes': 60,
    'minute': 60,
    'seconds': 1,
    'second': 1
}

_PREPOSITIONS = frozenset(('before', 'after'))

_DATE = re.compile(r'(\d\d\d\d)-(\d\d)-(\d\d)')


def _parse_time_24(s):
    
    m = _HHMMSS.fullmatch(s)
    
    if m is None:
        return None
    
    hour, minute, second = [int(g) for g in m.groups()]
    
    try:
        _check_int_range(hour, 0, 23)
        _check_int_range(minute, 0, 59)
        _check_int_range(second, 0, 59)
    except Exception:
        return None
    
    return Time(hour, minute, second)
    
    
def _check_int_range(i, min_, max_):
    if i < min_ or i > max_:
        raise ValueError()


def _parse_am_pm_time(s):
    
    parts = s.split()
    
    if len(parts) != 2 or parts[1] not in _AM_PM:
        return None
    
    try:
        hh, mm, ss = _parse_time_12(parts[0])
    except Exception:
        return None
    
    if hh == 12:
        hh = 0
        
    if parts[1].lower() == 'pm':
        hh += 12
        
    return Time(hh, mm, ss) 
    
    
def _parse_time_12(s):
    hh, mm, ss = _parse_time_12_aux(s)
    _check_int_range(hh, 1, 12)
    _check_int_range(mm, 0, 59)
    _check_int_range(ss, 0, 59)
    return (hh, mm, ss)


def _parse_time_12_aux(s):
    
    m = _HHMMSS.fullmatch(s)
    
    if m is not None:
        return [int(i) for i in m.groups()]
    
    m = _HHMM.fullmatch(s)

    if m is not None:
        return [int(i) for i in m.groups()] + [0]
    
    m = _HH.fullmatch(s)
    
    if m is not None:
        return [int(i) for i in m.groups()] + [0, 0]
    
    raise ValueError()
    

def _parse_time_name(s):
    return _NAMED_TIMES.get(s)


def _parse_event_name(s):
    if s in _TWILIGHT_EVENT_NAMES:
        name = _capitalize(s)
        return _TwilightEventTime(name, TimeDelta())
    else:
        return None
        

def _capitalize(s):
    return ' '.join(p.capitalize() for p in s.split())
    
    
_NONOFFSET_TIME_PARSE_FUNCTIONS = (
    _parse_time_24, _parse_am_pm_time, _parse_time_name, _parse_event_name)


def _parse_nonoffset_time(s):
    return _parse(s, _NONOFFSET_TIME_PARSE_FUNCTIONS)
    
    
def _parse(s, parse_functions):
    
    for f in parse_functions:
        
        result = f(s)
        
        if result is not None:
            return result
    
    # If we get here, no parse function could parse `s`.
    return None


def _parse_offset_time(s):
    
    parts = s.split()
    
    try:
        preposition, index = _parse_preposition(parts)
        event_name = _assemble_event_name(parts[index + 1:])
        offset = _parse_offset(parts[:index], preposition)
    except Exception:
        return None
    
    return _TwilightEventTime(event_name, offset)
    
    
def _parse_preposition(parts):
    
    for p in _PREPOSITIONS:
        try:
            index = parts.index(p)
        except ValueError:
            continue
        else:
            return (p, index)
    
    # If we get here, `parts` contains no preposition.
    raise ValueError()
    
    
def _assemble_event_name(parts):
    
    event_name = ' '.join(parts)
    
    if event_name not in _TWILIGHT_EVENT_NAMES:
        raise ValueError()
    
    return _capitalize(event_name)


def _parse_offset(parts, preposition):
    
    duration = _parse_duration(parts)

    if preposition == 'before':
        duration = -duration
        
    return duration
        
        
def _parse_duration(parts):
    
    if len(parts) == 1:
        return _parse_hhmmss_duration(parts[0])
    
    elif len(parts) == 2:
        return _parse_units_duration(parts[0], parts[1])
        
    else:
        raise ValueError()
    

def _parse_hhmmss_duration(hhmmss):
    
    m = _HHMMSS.fullmatch(hhmmss)
    
    if m is None:
        raise ValueError()
        
    hh, mm, ss = [int(i) for i in m.groups()]
    _check_int_range(hh, 0, 99)
    _check_int_range(mm, 0, 59)
    _check_int_range(ss, 0, 59)
    
    seconds = hh * 3600 + mm * 60 + ss
    
    return TimeDelta(seconds=seconds)
    
    
def _parse_units_duration(number, units):
    
    number = _parse_number(number)
    
    try:
        factor = _UNITS_FACTORS[units]
    except KeyError:
        raise ValueError()
    
    if not units.endswith('s') and number != 1:
        raise ValueError()
    
    seconds = number * factor
    
    return TimeDelta(seconds=seconds)


def _parse_number(s):
    
    for e in _NUMBER_RES:
        
        m = e.fullmatch(s)
        
        if m is not None:
            return float(m.group(0))
        
    return None


_TIME_PARSE_FUNCTIONS = (_parse_nonoffset_time, _parse_offset_time)


def _parse_time(s):
    return _parse(s, _TIME_PARSE_FUNCTIONS)


def _parse_date_time(s):
    
    parts = s.split(maxsplit=1)
    
    if len(parts) != 2:
        return None
    
    date = _parse_date(parts[0])
    if date is None:
        return None
    
    time = _parse_time(parts[1])
    if time is None:
        return None
    
    if isinstance(time, Time):
        return DateTime.combine(date, time)
    else:
        return _TwilightEventDateTime(date, time.event_name, time.offset)

    
def _parse_date(s):
    
    m = _DATE.fullmatch(s)
    
    if m is None:
        return None
    
    year, month, day = [int(i) for i in m.groups()]
    
    try:
        return Date(year, month, day)
    except ValueError:
        return None


class _TwilightEventTime:
     
     
    def __init__(self, event_name, offset=None):
         
        self.event_name = event_name
         
        if offset is None:
            self.offset = TimeDelta()
        else:
            self.offset = offset
         
         
    def resolve(self, location, date):
        return _resolve(date, self.event_name, location, self.offset)
         
         
class _TwilightEventDateTime:
     
     
    def __init__(self, date, event_name, offset=None):
         
        self.date = date
        self.event_name = event_name
         
        if offset is None:
            self.offset = TimeDelta()
        else:
            self.offset = offset
         
         
    def resolve(self, location):
        return _resolve(self.date, self.event_name, location, self.offset)
 
 
def _resolve(date, event_name, location, offset):
    
    sun_moon = _get_sun_moon(location)
    dt = sun_moon.get_solar_event_time(date, event_name)
     
    if dt is None:
        return None
     
    else:
        return dt + offset


_sun_moon_cache = {}


def _get_sun_moon(location):
    
    key = (location.latitude, location.longitude, location.time_zone)
    
    try:
        return _sun_moon_cache[key]
    
    except KeyError:
        # cache miss
        
        sun_moon = SunMoon(
            location.latitude, location.longitude, location.time_zone)
        
        _sun_moon_cache[key] = sun_moon
        
        return sun_moon
