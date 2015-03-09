"""Utility functions pertaining to time."""


import calendar
import datetime
import re


_MIN_YEAR = 1900
_MAX_YEAR = 2099


# The parsing functions of this module (`parse_date`, `parse_time`, and
# `parse_time_delta`) are intended for use in conjunction with regular
# expression parsing elsewhere. The basic idea is that the regular
# expressions are used to parse strings of certain numbers of digits,
# perhaps mixed with other things (e.g. strings of the form yyyy-mm-dd),
# and then the digit strings (e.g. yyyy, mm, and dd) are passed to one
# or more of the functions of this module to complete the parsing.
# In accordance with this paradigm, the parsing functions of this
# module assume that their arguments have a reasonable number of digits
# (e.g. two or four for a year, but not three), and do not check for this:
# they assume that such checking happened in the regular expression matching.


def parse_date(y, mm, dd):
    
    year = int(y)
    if year < 100:
        year += 2000 if year < 50 else 1900
        
    month = int(mm)
    day = int(dd)
    
    _check('year', y, check_year, year)
    _check('month', mm, check_month, month)
    _check('day', dd, check_day, day, year, month)
         
    return datetime.date(year, month, day)


def parse_time(hh, mm, ss=None, f=None):
    
    hour = int(hh)
    minute = int(mm)
    second = int(ss) if ss is not None else 0
    microsecond = _parse_fractional_second(f) if f is not None else 0
    
    _check('hour', hh, check_hour, hour)
    _check('minute', mm, check_minute, minute)
    _check('second', ss, check_second, second)
    
    return datetime.time(hour, minute, second, microsecond)


def _parse_fractional_second(f):
    
    # f is a string of fractional second digits that followed a decimal point
    
    # Get factor by which to multiply `f` to convert it to microseconds.
    factor = 10. ** (6 - len(f))
    
    return int(round(int(f) * factor))
        
    
def parse_time_delta(h, mm, ss=None, f=None):
    
    hours = int(h)
    minutes = int(mm)
    seconds = int(ss) if ss is not None else 0
    microseconds = _parse_fractional_second(f) if f is not None else 0
    
    _check('minutes', mm, check_minutes, minutes)
    _check('seconds', ss, check_seconds, seconds)
    
    return datetime.timedelta(
        hours=hours, minutes=minutes, seconds=seconds,
        microseconds=microseconds)
    
    
def _check(name, s, function, *args):
    try:
        function(*args)
    except ValueError:
        raise ValueError('Bad {:s} "{:s}".'.format(name, s))
    
    
def check_year(year):
    # We do not reject all future years since we can think of legitimate
    # uses for some, for example in tables of DST start and end times.
    if year < _MIN_YEAR or year > _MAX_YEAR:
        raise ValueError('Bad year {:d}.'.format(year))


def _check_range(val, min_val, max_val, name):
    if val < min_val or val > max_val:
        raise ValueError('Bad {:s} {:d}.'.format(name, val))
    
    
def check_month(month):
    _check_range(month, 1, 12, 'month')
    
    
def check_day(day, year, month):
    max_day = calendar.monthrange(year, month)[1]
    _check_range(day, 1, max_day, 'day')


def check_hour(hour):
    _check_range(hour, 0, 23, 'hour')
    
    
def check_minute(minute):
    _check_range(minute, 0, 59, 'minute')
    
    
def check_minutes(minutes):
    _check_range(minutes, 0, 59, 'minutes')
    
    
def check_second(second):
    _check_range(second, 0, 59, 'second')
    
    
def check_seconds(seconds):
    _check_range(seconds, 0, 59, 'seconds')


_DATE_RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)$')


# TODO: This is a bit of an odd duck. Move it somewhere else?
def parse_command_line_date(s):
    
    m = _DATE_RE.match(s)
     
    if m is None:
        raise ValueError('Bad date "{:s}".'.format(s))
     
    else:
        return parse_date(*m.groups())
