"""Functions pertaining to sound clip file names."""


import calendar
import datetime
import re


_FILE_NAME_RE = re.compile((
    r'^([a-zA-Z]+)_(\d{4})-(\d{2})-(\d{2})_(\d{2})\.(\d{2})\.(\d{2})_(\d{2})'
    r'\.[a-zA-Z0-9]+$'))

_FILE_NAME_RE_ALT = re.compile(
    r'^([a-zA-Z]+)_(\d{3})\.(\d{2})\.(\d{2})_(\d{2})\.[a-zA-Z0-9]+$')

_MIN_YEAR = 1900


def parse_clip_file_name(file_name):
    
    m = _FILE_NAME_RE.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
    
    else:
        
        (detector_name, year, month, day, hour, minute, second, num) = \
            m.groups()
        
        time = _get_time(
            year, month, day, hour, minute, second, num, file_name)
        
        return (detector_name, time)
    
    
def _raise_value_error(file_name, message=None):
    
    if message is None:
        message = 'Bad clip file name "{:s}".'.format(file_name)
    else:
        message = '{:s} in clip file name "{:s}".'.format(message, file_name)
        
    raise ValueError(message)
        

def _get_time(year, month, day, hour, minute, second, num, file_name):
    
    year = int(year)
    month = int(month)
    day = int(day)
    hour = int(hour)
    minute = int(minute)
    second = int(second)
    num = int(num)

    _check_year(year, file_name)
    _check_range(month, 1, 12, 'month', file_name)
    
    max_day = calendar.monthrange(year, month)[1]
    _check_range(day, 1, max_day, 'day', file_name)
            
    _check_range(hour, 0, 23, 'hour', file_name)
    _check_range(minute, 0, 59, 'minute', file_name)
    _check_range(second, 0, 59, 'second', file_name)
    
    if num > 9:
        _raise_value_error(
            file_name, 'Clip number {:d} is too high.'.format(num))
        
    return datetime.datetime(
        year, month, day, hour, minute, second, num * 100000)
        
    
def _check_year(year, file_name):
    if year < _MIN_YEAR:
        _raise_value_error(file_name, 'Bad year "{:d}"'.format(year))
        
        
def _check_range(val, min_val, max_val, name, file_name):
    if val < min_val or val > max_val:
        _raise_value_error(file_name, 'Bad {:s} "{:d}"'.format(name, val))
    
    
def parse_relative_clip_file_name(file_name):
    
    m = _FILE_NAME_RE_ALT.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
        
    else:
        
        (detector_name, hours, minutes, seconds, num) = m.groups()
        
        time = _get_time(
            '2001', '01', '01', hours, minutes, seconds, num, file_name)
        
        return (detector_name, time)
