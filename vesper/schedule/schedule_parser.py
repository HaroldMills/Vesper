"""Module containing functions that parse schedules."""


import datetime
import re


'''
time ::= nonrelative_time | relative_time

nonrelative_time ::= time_24 | am_pm_time | time_name | event_name

time_24 ::= h?h:mm:ss (with hour in [0, 23])
am_pm_time ::=  time_12 am_pm
time_12 ::= h?h:mm:ss | h?h:mm | h?h (with hour in [1, 12])
am_pm ::= 'am' | 'pm'
time_name ::= 'noon' | 'midnight'

event_name = 'sunrise' | 'sunset' | 'civil dawn' | 'civil dusk' |
    'nautical dawn' | 'nautical dusk' | 'astronomical dawn' |
    'astronomical dusk'
    
relative_time ::= offset preposition event_name
offset ::= hhmmss_offset | units_offset
hhmmss_offset ::= h?h:mm:ss
units_offset ::= number units (with number 1 if units singular)
number ::= d+ | d+.d* | .d+
units ::= 'hours' | 'hour' | 'minutes' | 'minute' | 'seconds' | 'second'
preposition = 'before' | 'after'

time examples:
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
    
date_time ::= date time
date ::= yyyy-mm-dd

date_time examples:
    2016-11-28 12:34:56
    2016-11-28 12 pm
    2016-11-28 noon
    2016-11-28 sunset
    2016-11-18 1 hour after sunset

example schedules:

    latitude: 42.5
    longitude: -70
    time_zone: EDT
    
    repeating_interval:
        start_time: 1 hour after sunset
        end_time: 30 minutes before sunrise
        first_interval_start_date: 2016-07-15
        last_interval_start_date: 2016-10-15
        
    interval:
        start_date_time: 2016-07-15 1 hour after sunset
        end_date_time: 2016-07-16 30 minutes before sunrise
'''


def parse_schedule(s):
    pass


class _EventRelativeTime:
    def __init__(self, event_name, offset):
        self.event_name = event_name
        self.offset = offset
        
        
class _EventRelativeDateTime:
    def __init__(self, date, event_name, offset):
        self.date = date
        self.event_name = event_name
        self.offset = offset


_HHMMSS = re.compile(r'(\d?\d):(\d\d):(\d\d)')
_HHMM = re.compile(r'(\d?\d):(\d\d)')
_HH = re.compile(r'(\d?\d)')

_AM_PM = frozenset(('am', 'pm'))

_NAMED_TIMES = {
    'noon': datetime.time(12),
    'midnight': datetime.time(0)
}

_EVENT_NAMES = frozenset((
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
    if s in _EVENT_NAMES:
        return _EventRelativeTime(s, datetime.timedelta())
    else:
        return None
    
    
_NONRELATIVE_TIME_PARSE_FUNCTIONS = (
    _parse_time_24, _parse_am_pm_time, _parse_time_name, _parse_event_name)


def _parse_nonrelative_time(s):
    return _parse(s, _NONRELATIVE_TIME_PARSE_FUNCTIONS)
    
    
def _parse(s, parse_functions):
    
    for f in parse_functions:
        
        result = f(s)
        
        if result is not None:
            return result
    
    # If we get here, no parse function could parse `s`.
    return None


def _parse_relative_time(s):
    
    parts = s.split()
    
    try:
        preposition, index = _parse_preposition(parts)
        event_name = _assemble_event_name(parts[index + 1:])
        offset = _parse_offset(parts[:index], preposition)
    except:
        return None
    
    return _EventRelativeTime(event_name, offset)
    
    
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
    
    if event_name not in _EVENT_NAMES:
        raise ValueError()
    
    return event_name


def _parse_offset(parts, preposition):
    
    if len(parts) == 1:
        seconds = _parse_hhmmss_offset(parts[0])
    
    elif len(parts) == 2:
        seconds = _parse_units_offset(parts[0], parts[1])
        
    else:
        raise ValueError()
    
    if preposition == 'before':
        seconds = -seconds
        
    return datetime.timedelta(seconds=seconds)
        
        
def _parse_hhmmss_offset(hhmmss):
    
    m = _HHMMSS.fullmatch(hhmmss)
    
    if m is None:
        raise ValueError()
        
    hh, mm, ss = [int(i) for i in m.groups()]
    _check_int_range(hh, 0, 23)
    _check_int_range(mm, 0, 59)
    _check_int_range(ss, 0, 59)
    
    return hh * 3600 + mm * 60 + ss
    
    
def _parse_units_offset(number, units):
    
    number = _parse_number(number)
    
    try:
        factor = _UNITS_FACTORS[units]
    except KeyError:
        raise ValueError()
    
    if not units.endswith('s') and number != 1:
        raise ValueError()
    
    return number * factor


def _parse_number(s):
    
    for e in _NUMBER_RES:
        
        m = e.fullmatch(s)
        
        if m is not None:
            return float(m.group(0))
        
    return None


_TIME_PARSE_FUNCTIONS = (_parse_nonrelative_time, _parse_relative_time)


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
        return _EventRelativeDateTime(date, time.event_name, time.offset)

    
def _parse_date(s):
    
    m = _DATE.fullmatch(s)
    
    if m is None:
        return None
    
    year, month, day = [int(i) for i in m.groups()]
    
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None
