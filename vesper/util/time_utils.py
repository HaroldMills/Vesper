"""Utility functions pertaining to time."""


import calendar
import datetime

import pytz


_MIN_YEAR = 1900
_MAX_YEAR = 2099


def create_utc_datetime(
        year, month, day, hour=0, minute=0, second=0, microsecond=0,
        time_zone=None, is_dst=None):
    
    """
    Creates a UTC `datetime.datetime` object.
    
    The date and time specified by the arguments to this function may
    be for a non-UTC time zone, in which case they are converted to UTC.
    The `time_zone` parameter indicates the time zone of the date and
    time specified by the arguments that precede it. It can be:
    
    * `None`, implying that the time zone of the other arguments is UTC.
    
    * a string acceptable as an argument to the `pytz.timezone` function,
      for example 'US/Eastern' or 'America/Costa_Rica'.
    
    * a `pytz` time zone object.
    
    When the `time_zone` argument is a time zone that observes DST,
    the `is_dst` argument can be used to disambiguate ambiguous local
    times, i.e. times in the interval [1:00:00, 2:00:00) on the day
    that DST ends. The value of the `is_dst` argument should be either
    `True`, `False`, or `None` (the default). The argument is ignored
    for nonambiguous times.
    
    :Raises ValueError:
        if an unrecognized time zone is specified, if a nonexistent
        local time is specified, or if an ambiguous time is specified
        and the `is_dst` argument is neither `True` nor `False` to
        resolve the ambiguity.
    """
    
    
    if time_zone is None:
        
        return datetime.datetime(
            year, month, day, hour, minute, second, microsecond, pytz.utc)
    
    else:
        
        if isinstance(time_zone, str):
            try:
                time_zone = pytz.timezone(time_zone)
            except pytz.UnknownTimeZoneError:
                raise ValueError(
                    'Unrecognized time zone "{:s}".'.format(time_zone))
        
        # Note that contrary to what one might think we should not do the
        # following:
        #
        #     dt = datetime.datetime(
        #         year, month day, hour, minute, second, microsecond,
        #         tzinfo=time_zone)
        #
        # since (as of 2015-05-21, at least) pytz time zones that
        # observer DST cannot be used as arguments to the standard
        # datetime constructor. See the "Example & Usage" section of
        # http://pytz.sourceforge.net for more information.
        dt = datetime.datetime(
            year, month, day, hour, minute, second, microsecond)
        
        # Note that if `is_dst` is `None`, the following will raise
        # an exception if the time `dt` is nonexistent or ambiguous
        # because of DST. See the "Problems with Localtime" section
        # of http://pytz.sourceforge.net for more information.
        try:
            dt = time_zone.localize(dt, is_dst=is_dst)
        except pytz.NonExistentTimeError:
            _raise_dst_value_error('does not exist', dt, time_zone)
        except pytz.AmbiguousTimeError:
            _raise_dst_value_error('is ambiguous', dt, time_zone)
        
        return dt.astimezone(pytz.utc)


def _raise_dst_value_error(fragment, dt, time_zone):
    raise ValueError((
        'Local time {:s} {:s} for time zone "{:s}" '
        'due to DST.').format(str(dt), fragment, str(time_zone)))


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
    return datetime.datetime(
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


def round_datetime(dt, unit_size):
    
    """
    Rounds a `datetime` according to the specified unit size.
    
    The unit size is specified in seconds.
    """
    
    seconds = _round_time(dt.time(), unit_size)
    delta = datetime.timedelta(seconds=seconds)
    return datetime.datetime(
        dt.year, dt.month, dt.day, tzinfo=dt.tzinfo) + delta


_ONE_DAY = 24 * 3600


def _round_time(time, unit_size):
    
    """
    Rounds a `time` to the specified unit size.
    
    The unit size is specified in seconds.
    
    This function returns a number of seconds rather than a `time`
    since in the return valuewe must be able to distinguish between
    the beginning and the end of a day.
    """
    
    # TODO: Allow subsecond unit sizes. This is a little tricky because of
    # floating point precision issues. We might require that the size be
    # at least one microsecond and that it divide one if it is smaller
    # than a second.
    
    if unit_size <= 0:
        raise ValueError(
            ('Time rounding unit size of {:g} seconds is not '
             'positive.').format(unit_size))
    
    elif unit_size % 1 != 0:
        raise ValueError(
            ('Time rounding unit size of {:g} seconds is not an '
             'integral number of seconds.').format(unit_size))
    
    elif _ONE_DAY % unit_size != 0:
        raise ValueError(
            ('Time rounding unit size of {:d} seconds does not evenly '
             'divide one day.').format(int(unit_size)))
        
    # Convert time to number of seconds.
    delta = datetime.timedelta(
        hours=time.hour, minutes=time.minute, seconds=time.second,
        microseconds=time.microsecond)
    seconds = delta.total_seconds()
    
    # Round number of seconds to nearest multiple of unit size.
    units = round(seconds / float(unit_size))
    return int(units * unit_size)
    

def round_time(time, unit_size):
    
    """
    Rounds a `time` according to the specified unit size.
    
    The unit size is specified in seconds.
    """
    
    seconds = _round_time(time, unit_size) % _ONE_DAY
    
    hour = seconds // 3600
    seconds -= hour * 3600
    minute = seconds // 60
    second = seconds % 60

    return datetime.time(hour=hour, minute=minute, second=second)
