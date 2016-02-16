"""Module containing `UsnoAltitudeAzimuthTable` class."""


from __future__ import print_function
import datetime
import re
# import urllib
# import urllib2

import pytz

import usno_utils


class UsnoAltitudeAzimuthTable(object):
    
    """
    Table of USNO altitudes and azimuths for the sun or moon.
    
    A `UsnoAltitudeAzimuthTable` contains altitudes and azimuths for
    the sun or moon for a single latitude, longitude, and day.
    
    Table data come from the United States Naval Observatory (USNO) web
    site. You can use the `download_table_text` static method to download
    a table.
    """
    
    @staticmethod
    def download_table_text(
            table_type, lat, lon, date, interval, utc_offset=None,
            place_name=None):
        
        return _download_table_text(
            table_type, place_name, lat, lon, date, utc_offset, interval)

    
    def __init__(self, table_text):
        
        self._text = table_text.strip()
        
        (self._type, self._place_name, self._lat, self._lon, self._date,
         self._utc_offset, self._data) = \
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
    def date(self):
        return self._date
     
    @property
    def utc_offset(self):
        return self._utc_offset
    
    @property
    def data(self):
        return self._data
    
    
_BODY_NUMS = {
    'Sun': 10,
    'Moon': 11
}

_TABLE_GENERATOR_URL = 'http://aa.usno.navy.mil/cgi-bin/aa_altazw.pl'

_PLACE_NAME_LINE_NUM = 4

_LOCATION_LINE_NUM = 6
_LOCATION_RE = re.compile(
    r'^([WE])([\d ]\d\d) (\d\d), ([NS])(\d\d) (\d\d)$')

_TABLE_TYPE_LINE_NUM = 8
_TABLE_TYPES = {
    'Altitude and Azimuth of the Sun': 'Sun',
    'Altitude and Azimuth of the Moon': 'Moon'
}

_DATE_LINE_NUM = 9
_MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'
_DATE_RE = re.compile(
    r'^(' + _MONTHS.replace(' ', '|') + r') (\d\d?), (\d\d\d\d)$')
_MONTH_NUMS = dict((name, i + 1) for i, name in enumerate(_MONTHS.split()))

_UTC_OFFSET_LINE_NUM = 11
_UTC_OFFSET_RE = re.compile(r'(\d+)(\.\d+)?h (West|East) of Greenwich')

_HEADER_SIZE = 19


'''
http://aa.usno.navy.mil/cgi-bin/aa_altazw.pl?
    form=2&
    body=11&
    year=2014&month=6&day=10&
    intv_mag=10&
    place=Sheep+Camp&
    lon_sign=-1&lon_deg=114&lon_min=01&
    lat_sign=1&lat_deg=46&lat_min=42&
    tz=7&tz_sign=-1
'''


def _download_table_text(
        table_type, place_name, lat, lon, date, utc_offset, interval):
    
    try:
        body = _BODY_NUMS[table_type]
    except KeyError:
        raise ValueError('Unrecognized table type "{}".'.format(table_type))
    
    if place_name is None:
        place_name = ''
        
    lat_sign, lat_degrees, lat_minutes = usno_utils.get_angle_data(lat)
    lon_sign, lon_degrees, lon_minutes = usno_utils.get_angle_data(lon)
    utc_offset_sign, utc_offset = \
        usno_utils.get_utc_offset_data(utc_offset, lon)
    
    values = (
        ('form', 2),
        ('body', body),
        ('place', place_name),
        ('year', date.year),
        ('month', date.month),
        ('day', date.day),
        ('intv_mag', interval),
        ('lat_sign', lat_sign),
        ('lat_deg', lat_degrees),
        ('lat_min', lat_minutes),
        ('lon_sign', lon_sign),
        ('lon_deg', lon_degrees),
        ('lon_min', lon_minutes),
        ('tz_sign', utc_offset_sign),
        ('tz', utc_offset)
    )
    
    return usno_utils.download_table(_TABLE_GENERATOR_URL, values)
    
    
def _parse_table(text):

    lines = text.split('\n')
      
    table_type, place_name, lat, lon, date, utc_offset = \
        _parse_table_header(lines)
      
    data = _parse_table_data(lines, table_type, date, utc_offset)
      
    return (table_type, place_name, lat, lon, date, utc_offset, data)
  
  
'''
Astronomical Applications Dept.                                               
U.S. Naval Observatory                                                        
Washington, DC 20392-5420
                                                    
SHEEP CAMP                                                                    
   o  ,    o  ,                                                               
W114 01, N46 42
                                                              
Altitude and Azimuth of the Sun                                               
Jun 10, 2014
                                                                 
Zone:  7h West of Greenwich
                                                  
          Altitude    Azimuth                                                 
                      (E of N)
                                               
 h  m         o           o                                                   
                                                                              
                                                                              
'''
def _parse_table_header(lines):
    place_name = _parse_place_name(lines)
    lat, lon = _parse_location(lines)
    table_type = _parse_table_type(lines)
    date = _parse_date(lines)
    utc_offset = _parse_utc_offset(lines)
    return (table_type, place_name, lat, lon, date, utc_offset)
  
  
def _parse_place_name(lines):
    return lines[_PLACE_NAME_LINE_NUM].strip()
  
  
# TODO: Move this to `usno_utils`? Note that the `_LOCATION_RE` here
# differs from that of `usno_rise_set_table`. Can one expression serve
# for both?
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
  
  
def _parse_table_type(lines):
      
    line = lines[_TABLE_TYPE_LINE_NUM].strip()
    
    try:
        return _TABLE_TYPES[line]
    
    except KeyError:
        _handle_header_parse_error('table type', _TABLE_TYPE_LINE_NUM)
      
      
def _parse_date(lines):
    
    line = lines[_DATE_LINE_NUM]
    m = _DATE_RE.match(line)
    
    if m is None:
        _handle_header_parse_error('date', _DATE_LINE_NUM)
        
    month = _MONTH_NUMS[m.group(1)]
    day = int(m.group(2))
    year = int(m.group(3))
    date = datetime.date(year, month, day)
    
    return date


def _handle_header_parse_error(name, line_num):
    raise ValueError(
        'Could not find {} in table header line {}.'.format(
            name, line_num + 1))
  
  
# TODO: Move this to `usno_utils`?
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
          
      
def _parse_table_data(lines, table_type, date, utc_offset):
    
    utc_offset = datetime.timedelta(hours=utc_offset)
    
    i = _HEADER_SIZE
    n = len(lines)
    data = []
           
    while i != n:
           
        line = lines[i].strip()
        i += 1
        
        if line != '':
            
            parts = line.split()
            
            time = _parse_time(parts[0], date, utc_offset)
            altitude = float(parts[1])
            azimuth = float(parts[2])
            
            if table_type == 'Sun':
                data.append((time, altitude, azimuth))
                
            else:
                illumination = float(parts[3])
                data.append((time, altitude, azimuth, illumination))
       
    return tuple(data)


def _parse_time(hhmm, date, utc_offset):
    hour, minute = hhmm.split(':')
    hour = int(hour)
    minute = int(minute)
    time = datetime.datetime(date.year, date.month, date.day, hour, minute)
    time -= utc_offset
    time = pytz.utc.localize(time)
    return time
