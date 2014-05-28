"""Utility functions pertaining to time."""


import calendar


_MIN_YEAR = 1900
_MAX_YEAR = 2099


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
