"""Functions pertaining to sound clip file names."""


import calendar
import datetime
import re

from nfc.util.bunch import Bunch


_DETECTOR_NAMES = frozenset(['Tseep'])
_EXTENSIONS = frozenset(['.wav'])

_FILE_NAME_RE = re.compile((
    r'^([a-zA-Z]+)_(\d{4})-(\d{2})-(\d{2})_(\d{2})\.(\d{2})\.(\d{2})_(\d{2})'
    r'\.([a-zA-Z0-9]+)$'))

_FILE_NAME_RE_ALT = re.compile(
    r'^([a-zA-Z]+)_(\d{3})\.(\d{2})\.(\d{2})_(\d{2})\.([a-zA-Z0-9]+)$')

_MIN_YEAR = 1900


def _get_current_year():
    return datetime.datetime.now().year


_current_year = _get_current_year()


def parse_clip_file_name(file_name):
    
    m = _FILE_NAME_RE.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
    
    else:
        
        (detector_name, year, month, day, hour, minute, second, num,
         extension) = m.groups()
        
        year = int(year)
        month = int(month)
        day = int(day)
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        num = int(num)
        extension = '.' + extension
        
        return _create_clip_info(
            detector_name, year, month, day, hour, minute, second, num,
            extension, file_name)
    
    
def parse_relative_clip_file_name(file_name):
    
    m = _FILE_NAME_RE_ALT.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
        
    else:
        
        (detector_name, hours, minutes, seconds, num, extension) = m.groups()
        
        hour = int(hours)
        minute = int(minutes)
        second = int(seconds)
        num = int(num)
        
        extension = '.' + extension
        
        return _create_clip_info(
            detector_name, 2001, 1, 1, hour, minute, second, num,
            extension, file_name)
        
    
def _create_clip_info(
    detector_name, year, month, day, hour, minute, second, num,
    extension, file_name):
    
    if detector_name not in _DETECTOR_NAMES:
        _raise_value_error(
            file_name,
            'Unrecognized detector name "{:s}"'.format(detector_name))
        
    if extension not in _EXTENSIONS:
        _raise_value_error(
            file_name,
            'Unrecognized file name extension "{:s}"'.format(extension))
        
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
        
    time = datetime.datetime(
        year, month, day, hour, minute, second, num * 100000)
    
    return Bunch(
        station_name=None,
        detector_name=detector_name,
        time=time)
    
    
def _raise_value_error(file_name, message=None):
    
    if message is None:
        message = 'Bad clip file name "{:s}".'.format(file_name)
    else:
        message = '{:s} in clip file name "{:s}".'.format(message, file_name)
        
    raise ValueError(message)
        

def _check_year(year, file_name):
    
    global _current_year
        
    if year < _MIN_YEAR:
        _raise_bad_year_error(year, file_name)
        
    if year > _current_year:
        # year is bad or `_current_year` needs updating
        
        _current_year = _get_current_year()
        
        if year > _current_year:
            # year is bad
            
            _raise_bad_year_error(file_name, year)
        
        
def _raise_bad_year_error(year, file_name):
    _raise_value_error(file_name, 'Bad year "{:d}"'.format(year))
        
        
def _check_range(val, min_val, max_val, name, file_name):
    if val < min_val or val > max_val:
        _raise_value_error(file_name, 'Bad {:s} "{:d}"'.format(name, val))
