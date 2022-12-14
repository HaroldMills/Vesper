"""Utility functions pertaining to time."""


from datetime import (
    date as Date,
    datetime as DateTime,
    time as Time,
    timedelta as TimeDelta)
from zoneinfo import ZoneInfo
import calendar
import math


_MIN_YEAR = 1900
_MAX_YEAR = 2099


def get_utc_now():
    return DateTime.now(ZoneInfo('UTC'))


def create_utc_datetime(
        year, month, day, hour=0, minute=0, second=0, microsecond=0,
        time_zone=None, fold=0):
    
    """
    Creates a UTC `datetime` object.
    
    The date and time specified by the arguments to this function may
    be for a non-UTC time zone, in which case they are converted to UTC.
    The `time_zone` parameter indicates the time zone of the date and
    time specified by the arguments that precede it. It can be:
    
    * `None`, implying that the time zone of the other arguments is UTC.
    
    * a string acceptable as an argument to the `zoneinfo.ZoneInfo`
      initializer, for example 'US/Eastern' or 'America/Costa_Rica'.
    
    * a `datetime.tzinfo` object.
    
    When the `time_zone` argument is for a time zone that observes DST,
    the `fold` argument can be used to disambiguate ambiguous local
    times, i.e. times in the interval [1:00:00, 2:00:00) on the day
    that DST ends. The value of the `fold` argument should be either
    `0` (the default) or `1`.
    
    :Raises ValueError:
        if an unrecognized time zone is specified.
    """
    
    
    if time_zone is None:
        
        return DateTime(
            year, month, day, hour, minute, second, microsecond,
            ZoneInfo('UTC'))
    
    else:
        
        if isinstance(time_zone, str):
            try:
                time_zone = ZoneInfo(time_zone)
            except:
                raise ValueError(
                    f'Could not get info for time zone "{time_zone}".')
        
        dt = DateTime(
            year, month, day, hour, minute, second, microsecond,
            time_zone, fold=fold)
        
        return dt.astimezone(ZoneInfo('UTC'))


# The parsing functions of this module (`parse_date_time`, `parse_date`,
# `parse_time`, and `parse_time_delta`) are intended for use in
# conjunction with regular expression parsing elsewhere. The basic idea
# is that the regular expressions are used to parse strings of certain
# numbers of digits, perhaps mixed with other things (e.g. strings of
# the form yyyy-mm-dd), and then the digit strings (e.g. yyyy, mm, and dd)
# are passed to one or more of the functions of this module to complete
# the parsing. In accordance with this paradigm, the parsing functions
# of this module assume that their arguments have a reasonable number
# of digits (e.g. two or four for a year, but not three), and do not
# check for this: they assume that such checking happened in the regular
# expression matching.


# TODO: Consider adding conversion to UTC to this function. That would
# decrease the chance of mistakes in such conversions, and encourage
# the conversion of times to UTC on input.
def parse_date_time(y, MM, dd, hh, mm, ss=None, f=None):
    d = parse_date(y, MM, dd)
    t = parse_time(hh, mm, ss, f)
    return DateTime(
        d.year, d.month, d.day, t.hour, t.minute, t.second, t.microsecond)
    
    
def parse_date(y, mm, dd):
    
    # We assume that `y` is a two- or four-digit string, and that
    # `mm` and `dd` are two-digit strings.
    
    year = int(y)
    if len(y) == 2:
        year += 2000 if year < 50 else 1900
        
    month = int(mm)
    day = int(dd)
    
    _check('year', y, check_year, year)
    _check('month', mm, check_month, month)
    _check('day', dd, check_day, day, year, month)
         
    return Date(year, month, day)


def parse_time(hh, mm, ss=None, f=None):
    
    hour = int(hh)
    minute = int(mm)
    second = int(ss) if ss is not None else 0
    microsecond = _parse_fractional_second(f) if f is not None else 0
    
    _check('hour', hh, check_hour, hour)
    _check('minute', mm, check_minute, minute)
    _check('second', ss, check_second, second)
    
    return Time(hour, minute, second, microsecond)


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
    
    return TimeDelta(
        hours=hours, minutes=minutes, seconds=seconds,
        microseconds=microseconds)
    
    
def _check(name, s, function, *args):
    try:
        function(*args)
    except ValueError:
        raise ValueError(f'Bad {name} "{s}".')
    
    
def check_year(year):
    # We do not reject all future years since we can think of legitimate
    # uses for some, for example in tables of DST start and end times.
    if year < _MIN_YEAR or year > _MAX_YEAR:
        raise ValueError(f'Bad year {year}.')


def _check_range(val, min_val, max_val, name):
    if val < min_val or val > max_val:
        raise ValueError(f'Bad {name} {val}.')
    
    
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


def round_timedelta(td, increment, mode='nearest'):
    
    """
    Rounds a `timedelta` according to the specified rounding increment.
    
    Parameters
    ----------
    td : timedelta
        the `timedelta` to be rounded.
        
    increment : int or float
        the rounding increment in seconds.
        
        If the rounding increment is less than one second, it must evenly
        divide one second. Otherwise it must evenly divide one day.
        
    mode: str
        the rounding mode, one of `"nearest"`, `"down"`, or `"up"`.
    
    Returns
    -------
    a rounded version of the specified `timedelta`.
    """

    
    # Decompose `td` into an integral number of days and a nonnegative
    # `TimeDelta` that is less than one day.
    days = TimeDelta(days=td.days)
    td = TimeDelta(seconds=td.seconds, microseconds=td.microseconds)
    
    rounded_td = _round_timedelta(td, increment, mode)
    
    return days + rounded_td


def _round_timedelta(td, increment, mode):
    
    _check_rounding_increment(increment)
    rounding_function = _get_rounding_function(mode)
    
    seconds = td.total_seconds()
    
    if increment >= 1:
        
        increment_count = rounding_function(seconds / increment)
        rounded_seconds = increment_count * increment
    
    else:
        # increment less than one second
        
        # Rounding the seconds fraction instead of the seconds when
        # the increment is less than a second reduces the maximum
        # possible size disparity between the value to be rounded
        # and the increment, perhaps reducing the possibility of
        # numerical issues. That might not be needed, but it won't
        # hurt.
        seconds_floor = math.floor(seconds)
        fraction = seconds - seconds_floor
        increment_count = rounding_function(fraction / increment)
        rounded_fraction = increment_count * increment
        rounded_seconds = seconds_floor + rounded_fraction
    
    return TimeDelta(seconds=rounded_seconds)


def _check_rounding_increment(increment):
    
    if increment <= 0:
        raise ValueError(
            f'Time rounding increment of {increment:g} seconds is not '
            f'positive.')
    
    elif increment >= 1:
        
        if _ONE_DAY % increment != 0:
            raise ValueError(
                f'Time rounding increment of {increment:d} seconds does not '
                f'evenly divide one day.')
    
    else:
        # unit size less than one second
        
        # Find how close to one second we can get with an integral
        # multiple of the increment, as a fraction of the increment.
        units_per_second = 1 / increment
        fraction = abs(units_per_second - round(units_per_second))
        
        if fraction > 1e-6:
            raise ValueError(
                f'Time rounding increment of {increment:g} seconds does '
                f'not evenly divide one second.')


def _get_rounding_function(mode):
    try:
        return _ROUNDING_FUNCTIONS[mode]
    except KeyError:
        raise ValueError(f'Unrecognized time rounding mode "{mode}".')


def round_datetime(dt, increment, mode='nearest'):
    
    """
    Rounds a `datetime` according to the specified rounding increment.
    
    Parameters
    ----------
    dt : datetime
        the `datetime` to be rounded.
        
    increment : int or float
        the rounding increment in seconds.
        
        If the rounding increment is less than one second, it must evenly
        divide one second. Otherwise it must evenly divide one day.
        
    mode: str
        the rounding mode, one of `"nearest"`, `"down"`, or `"up"`.
    
    Returns
    -------
    a rounded version of the specified `datetime`.
    """
    
    
    td = TimeDelta(
        hours=dt.hour, minutes=dt.minute, seconds=dt.second,
        microseconds=dt.microsecond)
    
    rounded_td = _round_timedelta(td, increment, mode)
    
    # Note that this keeps the time zone intact, if any.
    midnight = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    
    return midnight + rounded_td


_ONE_DAY = 24 * 3600

_ROUNDING_FUNCTIONS = {
    'nearest': round,
    'down': math.floor,
    'up': math.ceil
}


def round_time(time, increment, mode='nearest'):
    
    """
    Rounds a `time` according to the specified rounding increment.
    
    Parameters
    ----------
    time : time
        the `time` to be rounded.
        
    increment : int or float
        the rounding increment in seconds.
        
        If the rounding increment is less than one second, it must evenly
        divide one second. Otherwise it must evenly divide one day.
        
    mode: str
        the rounding mode, one of `"nearest"`, `"down"`, or `"up"`.
    
    Returns
    -------
    a rounded version of the specified `time`.
    """
    
    
    td = TimeDelta(
        hours=time.hour, minutes=time.minute, seconds=time.second,
        microseconds=time.microsecond)
    
    rounded_td = _round_timedelta(td, increment, mode)
    
    # Get time delta in seconds, wrapping 24 hours back to zero.
    seconds = rounded_td.total_seconds() % _ONE_DAY
    
    hour = int(seconds // 3600)
    seconds -= hour * 3600
    minute = int(seconds // 60)
    seconds -= minute * 60
    second = int(seconds)
    seconds -= second
    microsecond = int(1000000 * seconds)

    return Time(
        hour=hour, minute=minute, second=second, microsecond=microsecond)
