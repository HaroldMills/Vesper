"""Functions pertaining to sound clip file names."""


import datetime
import re

import nfc.util.time_utils as time_utils


_WAVE_EXTENSION = '.wav'

_ABSOLUTE_FILE_NAME_RE = re.compile((
    r'^([a-zA-Z]+)_(\d{4})-(\d{2})-(\d{2})_(\d{2})\.(\d{2})\.(\d{2})_(\d{2})'
    r'\.wav$'))

_RELATIVE_FILE_NAME_RE = re.compile(
    r'^([a-zA-Z]+)_(\d{3})\.(\d{2})\.(\d{2})_(\d{2})\.wav+$')


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
    
        tu = time_utils
        _check(file_name, 'year', tu.check_year, year)
        _check(file_name, 'month', tu.check_month, month)
        _check(file_name, 'day', tu.check_day, day, year, month)
        _check(file_name, 'hour', tu.check_hour, hour)
        _check(file_name, 'minute', tu.check_minute, minute)
        _check(file_name, 'second', tu.check_second, second)
        _check_num(num, file_name)
                    
        time = datetime.datetime(
            year, month, day, hour, minute, second, num * 100000)
        
        return (detector_name, time)
    
    
def _check(file_name, part_name, check, n, *args):
    try:
        check(n, *args)
    except ValueError:
        _raise_value_error(file_name, 'Bad {:s} "{:d}"'.format(part_name, n))
        
        
def _raise_value_error(file_name, message=None):
    
    if message is None:
        message = 'Bad clip file name "{:s}".'.format(file_name)
    else:
        message = '{:s} in clip file name "{:s}".'.format(message, file_name)
        
    raise ValueError(message)
        

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
    
        tu = time_utils
        _check(file_name, 'minutes', tu.check_minutes, minutes)
        _check(file_name, 'seconds', tu.check_seconds, seconds)
        _check_num(num, file_name)
            
        time_delta = datetime.timedelta(
            hours=hours, minutes=minutes, seconds=seconds,
            microseconds=num * 100000)

        return (detector_name, time_delta)
