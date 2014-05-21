"""Functions pertaining to sound clip file names."""


import calendar
import datetime
import re


_WAVE_EXTENSION = '.wav'

_ABSOLUTE_FILE_NAME_RE = re.compile((
    r'^([a-zA-Z]+)_(\d{4})-(\d{2})-(\d{2})_(\d{2})\.(\d{2})\.(\d{2})_(\d{2})'
    r'\.wav$'))

_RELATIVE_FILE_NAME_RE = re.compile(
    r'^([a-zA-Z]+)_(\d{3})\.(\d{2})\.(\d{2})_(\d{2})\.wav+$')

_MIN_YEAR = 1900


def is_clip_file_name(name):
    return name.endswith(_WAVE_EXTENSION)


def parse_absolute_clip_file_name(file_name):
    
    m = _ABSOLUTE_FILE_NAME_RE.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
    
    else:
        
        (detector_name, year, month, day, hour, minute, second, num) = \
            m.groups()
        
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        num = int(num)
    
        _check_year(year, file_name)
        _check_range(month, 1, 12, 'month', file_name)
        _check_day(year, month, day, file_name)
        _check_range(hour, 0, 23, 'hour', file_name)
        _check_range(minute, 0, 59, 'minute', file_name)
        _check_range(second, 0, 59, 'second', file_name)
        _check_num(num, file_name)
            
        time = datetime.datetime(
            year, month, day, hour, minute, second, num * 100000)
        
        return (detector_name, time)
    
    
def _raise_value_error(file_name, message=None):
    
    if message is None:
        message = 'Bad clip file name "{:s}".'.format(file_name)
    else:
        message = '{:s} in clip file name "{:s}".'.format(message, file_name)
        
    raise ValueError(message)
        

def _check_year(year, file_name):
    if year < _MIN_YEAR:
        _raise_value_error(file_name, 'Bad year "{:d}"'.format(year))
        
        
def _check_range(val, min_val, max_val, name, file_name):
    if val < min_val or val > max_val:
        _raise_value_error(file_name, 'Bad {:s} "{:d}"'.format(name, val))
    
    
def _check_day(year, month, day, file_name):
    max_day = calendar.monthrange(year, month)[1]
    _check_range(day, 1, max_day, 'day', file_name)
            

def _check_num(num, file_name):
    if num > 9:
        _raise_value_error(
            file_name, 'Clip number {:d} is too high.'.format(num))


def parse_relative_clip_file_name(file_name):
    
    m = _RELATIVE_FILE_NAME_RE.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
        
    else:
        
        (detector_name, hours, minutes, seconds, num) = m.groups()
        
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)
        num = int(num)
    
        _check_range(minutes, 0, 59, 'minutes', file_name)
        _check_range(seconds, 0, 59, 'seconds', file_name)
        _check_num(num, file_name)
            
        time_delta = datetime.timedelta(
            hours=hours, minutes=minutes, seconds=seconds,
            microseconds=num * 100000)

        return (detector_name, time_delta)
