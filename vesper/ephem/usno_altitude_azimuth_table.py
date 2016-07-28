"""Module containing class `UsnoAltitudeAzimuthTable`."""


import datetime
import re

import vesper.ephem.usno_table_class_utils as utils


class UsnoAltitudeAzimuthTable:
    
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
            table_type, lat, lon, date, interval, utc_offset, place_name)

    
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
    def body(self):
        return _BODY_NAMES[self._type]
    
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
    'Sun Altitude/Azimuth': 10,
    'Moon Altitude/Azimuth': 11
}

_BODY_NAMES = {
    'Sun Altitude/Azimuth': 'Sun',
    'Moon Altitude/Azimuth': 'Moon'
}

_TABLE_GENERATOR_URL = 'http://aa.usno.navy.mil/cgi-bin/aa_altazw.pl'

_PLACE_NAME_LINE_NUM = 4

_LOCATION_LINE_NUM = 6
_LOCATION_RE = re.compile(
    r'(^[WE ])(\d\d\d| \d\d|  \d) (\d\d| \d), ([NS ])(\d\d| \d) (\d\d| \d)$')

_TABLE_TYPE_LINE_NUM = 8
_TABLE_TYPES = {
    'Altitude and Azimuth of the Sun': 'Sun Altitude/Azimuth',
    'Altitude and Azimuth of the Moon': 'Moon Altitude/Azimuth'
}

_DATE_LINE_NUM = 9
_MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'
_DATE_RE = re.compile(
    r'^(' + _MONTHS.replace(' ', '|') + r') (\d\d?), (\d\d\d\d)$')
_MONTH_NUMS = dict((name, i + 1) for i, name in enumerate(_MONTHS.split()))

_UTC_OFFSET_LINE_NUM = 11

_HEADER_SIZE = 19


def _download_table_text(
        table_type, lat, lon, date, interval, utc_offset=None,
        place_name=None):
    
    try:
        body = _BODY_NUMS[table_type]
    except KeyError:
        raise ValueError('Unrecognized table type "{}".'.format(table_type))
    
    if place_name is None:
        place_name = ''
        
    lat_sign, lat_degrees, lat_minutes = utils.get_angle_data(lat)
    lon_sign, lon_degrees, lon_minutes = utils.get_angle_data(lon)
    utc_offset_sign, utc_offset = utils.get_utc_offset_data(utc_offset, lon)
    
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
    
    return utils.download_table(_TABLE_GENERATOR_URL, values)
    
    
def _parse_table(text):

    lines = text.split('\n')
      
    table_type, place_name, lat, lon, date, utc_offset = \
        _parse_table_header(lines)
      
    data = _parse_table_data(lines, table_type, date, utc_offset)
      
    return (table_type, place_name, lat, lon, date, utc_offset, data)
  
  
def _parse_table_header(lines):
    place_name = _parse_place_name(lines)
    lat, lon = utils.parse_location(lines, _LOCATION_LINE_NUM, _LOCATION_RE)
    table_type = _parse_table_type(lines)
    date = _parse_date(lines)
    utc_offset = utils.parse_utc_offset(lines, _UTC_OFFSET_LINE_NUM)
    return (table_type, place_name, lat, lon, date, utc_offset)
  
  
def _parse_place_name(lines):
    return lines[_PLACE_NAME_LINE_NUM].strip()
  
  
def _parse_table_type(lines):
      
    line = lines[_TABLE_TYPE_LINE_NUM].strip()
    
    try:
        return _TABLE_TYPES[line]
    
    except KeyError:
        utils.handle_header_parse_error('table type', _TABLE_TYPE_LINE_NUM)
      
      
def _parse_date(lines):
    
    line = lines[_DATE_LINE_NUM]
    m = _DATE_RE.match(line)
    
    if m is None:
        utils.handle_header_parse_error('date', _DATE_LINE_NUM)
        
    month = _MONTH_NUMS[m.group(1)]
    day = int(m.group(2))
    year = int(m.group(3))
    date = datetime.date(year, month, day)
    
    return date


def _parse_table_data(lines, table_type, date, utc_offset):
    
    i = _HEADER_SIZE
    n = len(lines)
    data = []
           
    while i != n:
           
        line = lines[i].strip()
        i += 1
        
        if line != '':
            
            parts = line.split()
            
            try:
                time = utils.parse_time(parts[0], date, utc_offset)
                
            except ValueError:
                # line does not start with time
            
                # Some tables include lines after the data lines, for
                # example to indicate that there are no such lines for
                # an empty table. We assume that the first such line
                # will not begin with a time.
                break
            
            altitude = float(parts[1])
            azimuth = float(parts[2])
            
            if table_type == 'Sun Altitude/Azimuth':
                data.append((time, altitude, azimuth))
                
            else:
                illumination = float(parts[3])
                data.append((time, altitude, azimuth, illumination))
       
    return tuple(data)
