"""
Module containing functions that compile schedule specifications.

A schedule specification is a dictionary with one of a number of
recognized forms. The result of compile the schedule is a `Schedule`
object.
"""


import datetime
import itertools
import re

import jsonschema
import pytz
import yaml

from vesper.schedule.schedule import Interval, Schedule
import vesper.ephem.ephem_utils as ephem_utils


'''
Grammar for schedule dates and times:

date ::= yyyy-mm-dd

time ::= nonoffset_time | offset_time

nonoffset_time ::= time_24 | am_pm_time | time_name | solar_event_name

time_24 ::= h?h:mm:ss (with hour in [0, 23])
am_pm_time ::=  time_12 am_pm
time_12 ::= h?h:mm:ss | h?h:mm | h?h (with hour in [1, 12])
am_pm ::= 'am' | 'pm'
time_name ::= 'noon' | 'midnight'
solar_event_name = 'sunrise' | 'sunset' | 'civil dawn' | 'civil dusk' |
    'nautical dawn' | 'nautical dusk' | 'astronomical dawn' |
    'astronomical dusk'
    
offset_time ::= offset preposition solar_event_name
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


# There are two sets of functions involved in compiling schedules, the
# *parse* functions and the *compile* functions. The parse functions
# parse schedule dates and/or times from strings, while the compile
# function compile dictionary schedule specifications into `Schedule`
# objects. The parse functions are lower-level than the compile
# functions, and are invoked by them.
 

_INTERVAL_SCHEMA = yaml.load('''
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


_INTERVALS_SCHEMA = yaml.load('''
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


_DAILY_SCHEMA = yaml.load('''
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


_UNION_SCHEMA = yaml.load('''
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

_ONE_DAY = datetime.timedelta(days=1)


def compile_schedule(spec, context):
    
    for compile in _schedule_compilers:
        schedule = compile(spec, context)
        if schedule is not None:
            return schedule
            
    raise ValueError('Schedule specification was not of a recognized type.')


def compile_interval_schedule(spec, context):
    
    try:
        interval = spec['interval']
    except KeyError:
        return None
    
    try:
        _check_spec_against_schema(spec, _INTERVAL_SCHEMA)
        interval = _compile_interval(interval, context)
    except ValueError as e:
        raise ValueError('Bad interval schedule: {}'.format(str(e)))
    
    return Schedule([interval])
    
    
def _check_spec_against_schema(spec, schema):
    try:
        jsonschema.validate(spec, schema)
    except jsonschema.exceptions.ValidationError as e:
        raise ValueError(e.message)
    
        
def _compile_interval(interval, context):
    
    start = interval.get('start')
    end = interval.get('end')
    duration = interval.get('duration')
    
    _check_interval_properties_count(start, end, duration)
        
    if start is None:
        end = _compile_date_time(end, context, 'end')
        duration = _compile_duration(duration)
        return Interval(end - duration, end)
        
    elif end is None:
        start = _compile_date_time(start, context, 'start')
        duration = _compile_duration(duration)
        return Interval(start, start + duration)
    
    else:
        start = _compile_date_time(start, context, 'start')
        end = _compile_date_time(end, context, 'end')
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
    
    
def _compile_date_time(dt, context, dt_name):
    
    if isinstance(dt, datetime.datetime):
        return _naive_to_utc(dt, context, dt_name)
    
    elif isinstance(dt, str):
        
        dt_text = dt
        dt = _parse_date_time(dt)
        
        if dt is None:
            raise ValueError('Bad interval {} "{}".'.format(dt_name, dt_text))
        
        if isinstance(dt, datetime.datetime):
            return _naive_to_utc(dt, context, dt_name, dt_text)
            
        else:
            _check_context_attribute(context.lat, 'latitude', dt_name, dt_text)
            _check_context_attribute(context.lon, 'longitude', dt_name, dt_text)
            return dt.resolve(context.lat, context.lon)
        
    else:
        raise ValueError(
            'Bad interval {} {}.'.format(dt_name, str(dt)))
        
    
def _naive_to_utc(dt, context, dt_name, dt_text=None):
    _check_context_attribute(context.time_zone, 'time zone', dt_name, dt_text)
    localized_dt = context.time_zone.localize(dt)
    return localized_dt.astimezone(pytz.utc)
    

def _check_context_attribute(value, name, dt_name, dt_text=None):
    
    if value is None:
        
        if dt_text is None:
            suffix = ''
        else:
            suffix =  ' "{}"'.format(dt_text)
            
        raise ValueError(
            'No {} available to resolve interval {}{}.'.format(
                name, dt_name, suffix))


def _compile_duration(duration):
    try:
        return _parse_duration(duration.split())
    except:
        raise ValueError('Bad interval duration "{}".'.format(duration))
    
    
def compile_intervals_schedule(spec, context):
    
    try:
        intervals = spec['intervals']
    except KeyError:
        return None
    
    try:
        _check_spec_against_schema(spec, _INTERVALS_SCHEMA)
        intervals = tuple(_compile_interval(i, context) for i in intervals)
    except ValueError as e:
        raise ValueError('Bad intervals schedule: {}'.format(str(e)))
    
    return Schedule(intervals)

    
def compile_daily_schedule(spec, context):
    
    try:
        daily = spec['daily']
    except KeyError:
        return None

    try:
        _check_daily_properties(spec)
        dates = _compile_daily_dates(daily)
        time_intervals = _compile_daily_time_intervals(daily)
        intervals = _compile_daily_intervals(dates, time_intervals, context)
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
    if isinstance(date, datetime.date):
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


def _compile_daily_intervals(dates, time_intervals, context):
    return tuple(_compile_daily_intervals_aux(dates, time_intervals, context))


def _compile_daily_intervals_aux(dates, time_intervals, context):
    
    combine = _combine_date_and_time
    
    for date in dates:
        
        for interval in time_intervals:
            
            if 'start' not in interval:
                end = combine(date, interval['end'], context, 'end')
                duration = interval['duration']
                yield Interval(end - duration, end)
                
            elif 'end' not in interval:
                start = combine(date, interval['start'], context, 'start')
                duration = interval['duration']
                yield Interval(start, start + duration)
                
            else:
                start = combine(date, interval['start'], context, 'start')
                end = combine(date, interval['end'], context, 'end')
                yield Interval(start, end)
            
            
def _combine_date_and_time(date, time, context, name):
    
    if isinstance(time, datetime.time):
        _check_context_attribute(context.time_zone, 'time zone', name)
        naive_dt = datetime.datetime.combine(date, time)
        localized_dt = context.time_zone.localize(naive_dt)
        return localized_dt.astimezone(pytz.utc)
        
    else:
        _check_context_attribute(context.lat, 'latitude', name)
        _check_context_attribute(context.lon, 'longitude', name)
        dt = _SolarEventDateTime(date, time.event_name, time.offset)
        return dt.resolve(context.lat, context.lon)


def compile_union_schedule(spec, context):
    
    try:
        union = spec['union']
    except KeyError:
        return None

    try:
        _check_spec_against_schema(spec, _UNION_SCHEMA)
    except ValueError as e:
        raise ValueError('Bad union schedule: {}'.format(str(e)))
    
    schedules = tuple(compile_schedule(s, context) for s in union)
    intervals = tuple(itertools.chain.from_iterable(
        s.get_intervals() for s in schedules))
    
    return Schedule(intervals)


_schedule_compilers = (
    compile_interval_schedule,
    compile_intervals_schedule,
    compile_daily_schedule,
    compile_union_schedule
)
 
    
_HHMMSS = re.compile(r'(\d?\d):(\d\d):(\d\d)')
_HHMM = re.compile(r'(\d?\d):(\d\d)')
_HH = re.compile(r'(\d?\d)')

_AM_PM = frozenset(('am', 'pm'))

_NAMED_TIMES = {
    'noon': datetime.time(12),
    'midnight': datetime.time(0)
}

_SOLAR_EVENT_NAMES = frozenset((
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
    except:
        return None
    
    return datetime.time(hour, minute, second)
    
    
def _check_int_range(i, min, max):
    if i < min or i > max:
        raise ValueError()


def _parse_am_pm_time(s):
    
    parts = s.split()
    
    if len(parts) != 2 or parts[1] not in _AM_PM:
        return None
    
    try:
        hh, mm, ss = _parse_time_12(parts[0])
    except:
        return None
    
    if hh == 12:
        hh = 0
        
    if parts[1] == 'pm':
        hh += 12
        
    return datetime.time(hh, mm, ss) 
    
    
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
    if s in _SOLAR_EVENT_NAMES:
        name = _capitalize(s)
        return _SolarEventTime(name, datetime.timedelta())
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
    except:
        return None
    
    return _SolarEventTime(event_name, offset)
    
    
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
    
    if event_name not in _SOLAR_EVENT_NAMES:
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
    
    return datetime.timedelta(seconds=seconds)
    
    
def _parse_units_duration(number, units):
    
    number = _parse_number(number)
    
    try:
        factor = _UNITS_FACTORS[units]
    except KeyError:
        raise ValueError()
    
    if not units.endswith('s') and number != 1:
        raise ValueError()
    
    seconds = number * factor
    
    return datetime.timedelta(seconds=seconds)


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
    
    if isinstance(time, datetime.time):
        return datetime.datetime.combine(date, time)
    else:
        return _SolarEventDateTime(date, time.event_name, time.offset)

    
def _parse_date(s):
    
    m = _DATE.fullmatch(s)
    
    if m is None:
        return None
    
    year, month, day = [int(i) for i in m.groups()]
    
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


class _SolarEventTime:
     
     
    def __init__(self, event_name, offset=None):
         
        self.event_name = event_name
         
        if offset is None:
            self.offset = datetime.timedelta()
        else:
            self.offset = offset
         
         
    def resolve(self, lat, lon, date):
        return _resolve(date, self.event_name, lat, lon, self.offset)
         
         
class _SolarEventDateTime:
     
     
    def __init__(self, date, event_name, offset=None):
         
        self.date = date
        self.event_name = event_name
         
        if offset is None:
            self.offset = datetime.timedelta()
        else:
            self.offset = offset
         
         
    def resolve(self, lat, lon):
        return _resolve(self.date, self.event_name, lat, lon, self.offset)
 
 
def _resolve(date, event_name, lat, lon, offset):
     
    dt = ephem_utils.get_event_time(event_name, lat, lon, date)
     
    if dt is None:
        return None
     
    else:
        return dt + offset
