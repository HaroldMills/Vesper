"""Utility functions for use in USNO table classes."""


import datetime
import math
import re
import urllib

import pytz


_PRE_BEGIN = '<pre>'
_PRE_END = '</pre>'

_UTC_OFFSET_RE = re.compile(r'(\d+)(\.\d+)?h (West|East) of Greenwich')


def get_angle_data(x):
    sign = get_sign(x)
    x = abs(x)
    degrees = int(math.floor(x))
    minutes = int(round(60 * (x - degrees)))
    return (sign, degrees, minutes)


def get_sign(x):
    return 1 if x >= 0 else -1


def get_utc_offset_data(utc_offset, lon):
    
    if utc_offset is None:
        utc_offset = int(round(24 * (lon / 360.)))
        
    sign = get_sign(utc_offset)
    offset = abs(utc_offset)
    
    # We format the offset as a string with up to two digits after
    # the decimal point. The USNO site accepts that, but rejects an
    # offset with too many digits after the decimal point.
    offset = '{:.2g}'.format(offset)
    
    return (sign, offset)


def download_table(url, values):
    
    # We append the values to the URL as a query rather than passing
    # them separately as the `data` argument of the `urllib2.Request`
    # initializer to make the request a GET rather than a POST. (A
    # `urllib2.Request` initialized with a non-`None` `data` argument
    # is a POST, while one initialized without a `data` argument is a
    # GET. See the documentation for the `urllib2.Request` class at
    # https://docs.python.org/2/library/urllib2.html#module-urllib2
    # for details.)
    #
    # We have found (as of 2016-02-17) that altitude/azimuth tables
    # must be retrieved with GET requests, while rise/set tables can
    # be retrieved with either GET or POST. When we attempt to retrieve
    # an altitude/azimuth table with a POST request the response has
    # status code 200 but instead of a table the response text
    # contains the message "Error:  Location/coordinates not defined".
    query = urllib.parse.urlencode(values)
    url += '?' + query
    
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request)
    html = response.read()
    
    start = html.find(_PRE_BEGIN) + len(_PRE_BEGIN)
    end = html.find(_PRE_END)
    text = html[start:end].strip('\n') + '\n'
     
    return text


def parse_location(lines, line_num, location_re):
    
    line = lines[line_num]
    m = location_re.search(line)
    
    if m is None:
        handle_header_parse_error('location', line_num)
        
    lon_dir, lon_deg, lon_min, lat_dir, lat_deg, lat_min = m.groups()
    lat = _get_angle(lat_dir, 'N', lat_deg, lat_min)
    lon = _get_angle(lon_dir, 'E', lon_deg, lon_min)
    
    return (lat, lon)


def _get_angle(direction, positive_direction, degrees, minutes):
    sign = 1 if direction == ' ' or direction == positive_direction else -1
    return sign * (int(degrees) + int(minutes) / 60.)


def parse_utc_offset(lines, line_num):
    
    line = lines[line_num]
    
    if line.find('Universal Time') != -1:
        return datetime.timedelta(hours=0)
    
    m = _UTC_OFFSET_RE.search(line)
    
    if m is None:
        handle_header_parse_error('UTC offset', line_num)
        
    hour, fraction, direction = m.groups()
    sign = 1 if direction == 'East' else -1
    hour = int(hour)
    fraction = 0. if fraction is None else float(fraction)
    hours = sign * (hour + fraction)
    
    return datetime.timedelta(hours=hours)


def handle_header_parse_error(name, line_num):
    raise ValueError(
        'Could not find {} in table header line {}.'.format(
            name, line_num + 1))


def parse_time(hhmm, date, utc_offset):
    s = '{:4d}-{:02d}-{:02d} {}'.format(date.year, date.month, date.day, hhmm)
    try:
        time = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M')
    except ValueError:
        raise ValueError('Bad time "{}".'.format(hhmm))
    return naive_to_utc(time, utc_offset)


def naive_to_utc(time, utc_offset):
    time -= utc_offset
    return pytz.utc.localize(time)
