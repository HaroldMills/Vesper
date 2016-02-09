"""
Utility functions for retrieving and parsing sun and moon data from the
United States Naval Observatory (USNO).
"""


from __future__ import print_function
import datetime
import math
import re
import urllib
import urllib2

import pytz


class UsnoSunMoonTable(object):
    
    
    @staticmethod
    def download_table_text(
            table_type, lat, lon, year, utc_offset=None, place_name=None):
        
        return _download_table_text(
            table_type, place_name, lat, lon, year, utc_offset)

    
    def __init__(self, table_text):
        
        self._text = table_text
        
        (self._type, self._place_name, self._lat, self._lon, self._year,
         self._utc_offset, self._rising_times, self._setting_times) = \
            _parse_table(self._text)
             
    
    @property
    def text(self):
        return self._text
    
    @property
    def type(self):
        return self._type
    
    @property
    def place_name(self):
        return self._place_name
    
    @property
    def lat(self):
        return self._lat
    
    @property
    def lon(self):
        return self._lon
    
    @property
    def year(self):
        return self._year
    
    @property
    def utc_offset(self):
        return self._utc_offset
    
    @property
    def rising_times(self):
        return self._rising_times
    
    @property
    def setting_times(self):
        return self._setting_times
    
    
TABLE_TYPE_SUNRISE_SUNSET = 0
TABLE_TYPE_MOONRISE_MOONSET = 1
TABLE_TYPE_CIVIL_TWILIGHT = 2
TABLE_TYPE_NAUTICAL_TWILIGHT = 3
TABLE_TYPE_ASTRONOMICAL_TWILIGHT = 4


_TABLE_TYPES = (
    'Sunrise/Sunset',
    'Moonrise/Moonset',
    'Civil Twilight',
    'Nautical Twilight',
    'Astronomical Twilight'
)

_TABLE_TYPE_NUMS = dict((name, i) for i, name in enumerate(_TABLE_TYPES))

_USNO_TABLE_GENERATOR_URL = 'http://aa.usno.navy.mil/cgi-bin/aa_rstablew.pl'
_PRE_BEGIN = '<pre>'
_PRE_END = '</pre>'

_TABLE_TYPE_LINE_NUM = 1
_TABLE_TYPE_NAMES = (
    'Rise and Set for the Sun',
    'Rise and Set for the Moon',
    'Civil Twilight',
    'Nautical Twilight',
    'Astronomical Twilight'
)

_PLACE_NAME_LINE_NUM = 0
_PLACE_NAME_START_INDEX = 25
_PLACE_NAME_END_INDEX = 103

_LOCATION_LINE_NUM = 1
_LOCATION_RE = re.compile(
    r'Location: ([WE ])(\d\d\d) (\d\d), ([NS ])(\d\d) (\d\d)')

_YEAR_LINE_NUM = 1
_YEAR_RE = re.compile(r'(\d\d\d\d)')

_UTC_OFFSET_LINE_NUM = 3
_UTC_OFFSET_RE = re.compile(r'(\d+)(\.\d+)?h (West|East) of Greenwich')

_HEADER_SIZE = 9
_RISE_OFFSET = 4
_SET_OFFSET = 9
_MONTH_WIDTH = 11


def _download_table_text(table_type, place_name, lat, lon, year, utc_offset):
    
    try:
        table_type = _TABLE_TYPE_NUMS[table_type]
    except KeyError:
        raise ValueError('Unrecognized table type "{:s}".'.format(table_type))
    
    if place_name is None:
        place_name = ''
        
    lat_sign, lat_degrees, lat_minutes = _get_angle_data(lat)
    lon_sign, lon_degrees, lon_minutes = _get_angle_data(lon)
    
    if utc_offset is None:
        utc_offset = 24 * (lon / 360.)
    
    utc_offset_sign = _get_sign(utc_offset)
    
    values = {
        'FFX': 2,
        'type': table_type,
        'place': place_name,
        'yy0': lat_sign,
        'yy1': lat_degrees,
        'yy2': lat_minutes,
        'xx0': lon_sign,
        'xx1': lon_degrees,
        'xx2': lon_minutes,
        'xxy': year,
        'zz0': utc_offset_sign,
        'zz1': abs(utc_offset),
        'ZZZ': 'END'
    }
    
    data = urllib.urlencode(values)
    request = urllib2.Request(_USNO_TABLE_GENERATOR_URL, data)
    response = urllib2.urlopen(request)
    html = response.read()
    
    start = html.find(_PRE_BEGIN) + len(_PRE_BEGIN)
    end = html.find(_PRE_END)
    text = html[start:end].strip('\n') + '\n'
    
    return text
    
    
def _get_angle_data(x):
    sign = _get_sign(x)
    x = sign * x
    degrees = int(math.floor(x))
    minutes = int(round(60 * (x - degrees)))
    return (sign, degrees, minutes)


def _get_sign(x):
    return 1 if x >= 0 else -1


def _parse_table(text):
    
    lines = text.split('\n')
    lines = _strip_leading_and_trailing_blank_lines(lines)
    
    table_type, place_name, lat, lon, year, utc_offset = \
        _parse_table_header(lines)
    
    rising_times = _parse_table_times(lines, year, utc_offset, _RISE_OFFSET)
    setting_times = _parse_table_times(lines, year, utc_offset, _SET_OFFSET)
    
    return (table_type, place_name, lat, lon, year, utc_offset,
            rising_times, setting_times)


def _strip_leading_and_trailing_blank_lines(lines):
    
    end = len(lines)
    
    start = 0
    while start != end and lines[start].strip() == '':
        start += 1
        
    while end != 0 and lines[end - 1].strip() == '':
        end -= 1
        
    return lines[start:end]
        
        
def _parse_table_header(lines):
    table_type = _parse_table_type(lines)
    place_name = _parse_place_name(lines)
    lat, lon = _parse_location(lines)
    year = _parse_year(lines)
    utc_offset = _parse_utc_offset(lines)
    return (table_type, place_name, lat, lon, year, utc_offset)


def _parse_table_type(lines):
    
    line = lines[_TABLE_TYPE_LINE_NUM]
    
    for i, name in enumerate(_TABLE_TYPE_NAMES):
        if line.find(name) != -1:
            return _TABLE_TYPES[i]
        
    # If we get here, we couldn't find any of the known table type
    # names in the table type line.
    _handle_header_parse_error('table type', _TABLE_TYPE_LINE_NUM)
    
    
def _handle_header_parse_error(name, line_num):
    raise ValueError(
        'Could not find {:s} in table header line {:d}.'.format(
            name, line_num + 1))


def _parse_place_name(lines):
    line = lines[_PLACE_NAME_LINE_NUM]
    name = line[_PLACE_NAME_START_INDEX:_PLACE_NAME_END_INDEX].strip()
    return name


def _parse_location(lines):
    
    line = lines[_LOCATION_LINE_NUM]
    m = _LOCATION_RE.search(line)
    
    if m is None:
        _handle_header_parse_error('location', _LOCATION_LINE_NUM)
        
    lon_dir, lon_deg, lon_min, lat_dir, lat_deg, lat_min = m.groups()
    lat = _get_angle(lat_dir, 'N', lat_deg, lat_min)
    lon = _get_angle(lon_dir, 'E', lon_deg, lon_min)
    
    return (lat, lon)


def _get_angle(direction, positive_direction, degrees, minutes):
    sign = 1 if direction == ' ' or direction == positive_direction else -1
    return sign * (int(degrees) + int(minutes) / 60.)


def _parse_year(lines):
    
    line = lines[_YEAR_LINE_NUM]
    m = _YEAR_RE.search(line)
    
    if m is None:
        _handle_header_parse_error('year', _YEAR_LINE_NUM)
        
    year = int(m.group(0))
    
    return year

        
def _parse_utc_offset(lines):
    
    line = lines[_UTC_OFFSET_LINE_NUM]
    
    if line.find('Universal Time') != -1:
        return 0.
    
    m = _UTC_OFFSET_RE.search(line)
    
    if m is None:
        _handle_header_parse_error('UTC offset', _UTC_OFFSET_LINE_NUM)
        
    hour, fraction, direction = m.groups()
    sign = 1 if direction == 'East' else -1
    hour = int(hour)
    fraction = 0. if fraction is None else float(fraction)
    offset = sign * (hour + fraction)
    
    return offset
        
    
def _parse_table_times(lines, year, utc_offset, time_column_offset):
    
    utc_offset = datetime.timedelta(hours=utc_offset)
    
    i = _HEADER_SIZE
    n = len(lines)
    times = []
        
    while i != n:
        
        line = lines[i]
        i += 1
        
        try:
            day = int(line[:2])
            
        except ValueError:
            # line does not start with two digits
            
            # Some tables include lines after the day lines, for example
            # to include a table key. We assume that the first such line
            # will not begin with two digits.
            
            break
        
        for j in xrange(12):
            
            month = j + 1
            
            k = time_column_offset + j * _MONTH_WIDTH
            time = line[k:k + 4]
            
            try:
                hour = int(time[:2])
                
            except ValueError:
                # table does not have time at this line and month
                continue
            
            else:
                # table has time at this line and month
            
                minute = int(time[2:])
                time = datetime.datetime(year, month, day, hour, minute)
                time -= utc_offset
                time = pytz.utc.localize(time)
                times.append(time)
               
    # Put times in increasing order.
    times.sort()
    
    return tuple(times)
