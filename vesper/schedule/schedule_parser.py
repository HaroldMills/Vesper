"""Module containing functions that parse schedules."""


'''
time ::= time_24 | am_pm_time | time_name | event_name | event_relative_time

time_24 ::= h?h:mm:ss (with hour in [0, 23])
am_pm_time ::=  time_12 am_pm
time_12 ::= h?h:mm:ss | h?h:mm | h?h (with hour in [1, 12])
am_pm ::= 'am' | 'pm'
time_name ::= 'noon' | 'midnight'

event_name = 'sunrise' | 'sunset' | 'civil dawn' | 'civil dusk' |
    'nautical dawn' | 'nautical dusk' | 'astronomical dawn' |
    'astronomical dusk'
    
event_relative_time ::= offset preposition event_name
offset ::= hhmmss_offset | units_offset
hhmmss_offset ::= h?h:mm:ss
units_offset ::= number units (with number 1 if units singular)
number ::= d+ | d+.d* | .d+
units ::= 'hours' | 'hour' | 'minutes' | 'minute' | 'seconds' | 'second'
preposition = 'before' | 'after'

daily_time examples:
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
    
schedule:

    latitude: 42.5
    longitude: -70
    time_zone: EDT
    
    repeated_interval:
        start_time: 1 hour after sunset
        end_time: 30 minutes before sunrise
        filter_start_date_time: 2016-07-15 noon
        filter_end_date_time: 2016-10-16 noon
'''


import datetime
import re


class _RelativeTime:
    
    def __init__(self, event_name, offset):
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
        return _RelativeTime(s, datetime.timedelta())
    else:
        return None
    
    
def _parse_relative_time(s):
    
    parts = s.split()
    
    try:
        preposition, index = _parse_preposition(parts)
        event_name = _assemble_event_name(parts[index + 1:])
        offset = _parse_offset(parts[:index], preposition)
    except:
        return None
    
    return _RelativeTime(event_name, offset)
    
    
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


_PARSE_FUNCTIONS = (
    _parse_time_24, _parse_am_pm_time, _parse_time_name,
    _parse_event_name, _parse_relative_time)


def _parse_time(s):
    
    for f in _PARSE_FUNCTIONS:
        
        result = f(s)
        
        if result is not None:
            return result
    
    # If we get here, no parse function could parse `s`.
    raise ValueError('Could not parse time "{}".'.format(s))


def _main():
    s = '.5 hours before civil dusk'
    time = _parse_time(s)
    if isinstance(time, _RelativeTime):
        print('{}, {}'.format(time.event_name, time.offset.total_seconds()))
    else:
        print(time)
    

if __name__ == '__main__':
    _main()
    
    
# The code below uses the `pyparsing` module to parse times. It is
# considerably shorter than the `_parse_time` function and related
# functions above, but it is less portable to other languages than
# that code. I chose to write and use the longer code after writing
# the shorter code because I anticipate wanting to port the code to
# JavaScript.
#
#
# from pyparsing import (
#     Group, oneOf, ParseException, Regex, Suppress, White)
#
#
# _ZEROS = ['00', '00']
# 
# def _parse_am_pm_time_tokens(tokens):
#     parts = tokens[0].split(':')
#     parts += _ZEROS[:3 - len(parts)]
#     hh, mm, ss = [int(i) for i in parts]
#     _check_int_range(hh, 1, 12, 'hour')
#     _check_int_range(mm, 0, 59, 'minute')
#     _check_int_range(ss, 0, 59, 'second')
#     if hh == 12:
#         hh = 0
#     if tokens[1] == 'pm':
#         hh += 12
#     return datetime.time(hh, mm, ss)        
#     
# def _parse_hhmmss_time_tokens(tokens):
#     parts = tokens[0].split(':')
#     hh, mm, ss = [int(i) for i in parts]
#     _check_int_range(hh, 0, 23, 'hour')
#     _check_int_range(mm, 0, 59, 'minute')
#     _check_int_range(ss, 0, 59, 'second')
#     return datetime.time(hh, mm, ss)
#     
# def _parse_named_time_tokens(tokens):
#     hh = 12 if tokens[0] == 'noon' else 0
#     return datetime.time(hh)
# 
# _HHMMSS_RE = r'\d?\d:\d\d:\d\d'
# 
# _HHMMSS = Regex(_HHMMSS_RE)
# _HHMM = Regex(r'\d?\d:\d\d')
# _HH = Regex(r'\d?\d')
# 
# _ = Suppress(White(ws=' ', exact=1))
# 
# _AM_PM_TIME = \
#     ((_HHMMSS | _HHMM | _HH) + _ + oneOf('am pm')).setParseAction(
#         _parse_am_pm_time_tokens)
# 
# _HHMMSS_TIME = Regex(_HHMMSS_RE).setParseAction(_parse_hhmmss_time_tokens)
# 
# _NAMED_TIME = oneOf('noon midnight').setParseAction(_parse_named_time_tokens)
# 
# _TIME_OF_DAY = _AM_PM_TIME | _HHMMSS_TIME | _NAMED_TIME
# 
# 
# def _parse_hhmmss_offset_tokens(tokens):
#     hh, mm, ss = [int(i) for i in tokens[0].split(':')]
#     _check_int_range(hh, 0, 24, 'hours')
#     _check_int_range(mm, 0, 59, 'minutes')
#     _check_int_range(ss, 0, 59, 'seconds')
#     return hh * 3600 + mm * 60 + ss
# 
# def _check_int_range(i, min, max, units):
#     if i < min or i > max:
#         raise ParseException('Bad {} value {}.'.format(units, i))
#     
# def _parse_float_token(tokens):
#     return float(tokens[0])
# 
# def _check_units_offset_tokens(tokens):
#     number, units = tokens[0]
#     if not units.endswith('s') and number != 1:
#         raise ParseException('Number with singular time units must be 1.')
#     
# _HHMMSS_OFFSET = \
#     Regex(r'\d?\d:\d\d:\d\d').setParseAction(_parse_hhmmss_offset_tokens)
# 
# _NUMBER = \
#     (Regex(r'\d+\.\d*') | Regex(r'\.\d+') | Regex(r'\d+')).setParseAction(
#         _parse_float_token)
#     
# _UNITS = oneOf(['hours', 'hour', 'minutes', 'minute', 'seconds', 'second'])
# 
# _UNITS_OFFSET = \
#     Group(_NUMBER('number') + _UNITS('units')).setParseAction(
#         _check_units_offset_tokens)
#     
# _PREPOSITION = oneOf('before after')
# 
# _EVENT_NAME = oneOf([
#     'sunrise', 'sunset', 'civil dawn', 'civil dusk', 'nautical dawn',
#     'nautical dusk', 'astronomical dawn', 'astronomical dusk'])
# 
# _HHMMSS_RELATIVE_TIME = \
#     _HHMMSS_OFFSET('offset') + _ + _PREPOSITION('preposition') + _ + \
#     _EVENT_NAME('event_name')
#     
# _UNITS_RELATIVE_TIME = \
#     _UNITS_OFFSET('offset') + _ + _PREPOSITION('preposition') + _ + \
#     _EVENT_NAME('event_name')
#
#
# def _parse_hhmmss_time(s):
#     return _HHMMSS_TIME.parseString(s)[0]
#     
#     
# def _parse_am_pm_time(s):
#     return _AM_PM_TIME.parseString(s)[0]
# 
# 
# def _parse_named_time(s):
#     return _NAMED_TIME.parseString(s)[0]
# 
# 
# def _parse_hhmmss_relative_time(s):
#     
#     result = _HHMMSS_RELATIVE_TIME.parseString(s)
#     
#     seconds = result.offset
#     if result.preposition == 'before':
#         seconds = -seconds
#     offset = datetime.timedelta(seconds=seconds)
#         
#     return RelativeTime(result.event_name, offset)
#     
#     
# def _parse_units_relative_time(s):
#     
#     result = _UNITS_RELATIVE_TIME.parseString(s)
#     
#     number, units = result.offset
#     if units.startswith('h'):
#         seconds = number * 3600
#     elif units.startswith('m'):
#         seconds = number * 60
#     else:
#         seconds = number
#         
#     if result.preposition == 'before':
#         seconds = -seconds
#         
#     offset = datetime.timedelta(seconds=seconds)
#     
#     return RelativeTime(result.event_name, offset)
