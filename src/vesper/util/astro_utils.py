"""
Utility functions that calculate sunrise and sunset times.

This module includes functions for calculating sunrise and sunset times
as well as civil, nautical, and astronomical dawn and dusk times. The
module relies on PyEphem (http://rhodesmill.org/pyephem) to calculate
these times.

See comments in the `test_ephem` script for the results of an extensive
comparison of times computed by PyEphem to times from tables computed
by the United States Naval Observatory (USNO). In short, thousands of
comparisons found no PyEphem times at latitudes below the polar circles
that differed from the corresponding USNO times by more than one minute,
with most in agreement. A small number of comparisons at latitudes above
the arctic circles found larger differences of up to five minutes. For
latitudes above the polar circles PyEphem also reports twilight dawn
and dusk times for some dates for which the USNO does not, and vice
versa.
"""


import datetime
import math

import ephem
import pytz


_SUN = ephem.Sun()
_MOON = ephem.Moon()

_RISE_SET_HORIZON = '-0:34'
_CIVIL_HORIZON = '-6'
_NAUTICAL_HORIZON = '-12'
_ASTRONOMICAL_HORIZON = '-18'

_ALMOST_ONE_DAY = \
    datetime.timedelta(days=1) - datetime.timedelta(microseconds=1)


def get_sunrise_time(lat, lon, date):
    return _get_rising_time(lat, lon, date, _SUN, _RISE_SET_HORIZON)


def get_sunset_time(lat, lon, date):
    return _get_setting_time(lat, lon, date, _SUN, _RISE_SET_HORIZON)


def get_civil_dawn_time(lat, lon, date):
    return _get_rising_time(
        lat, lon, date, _SUN, _CIVIL_HORIZON, use_center=True)


def get_civil_dusk_time(lat, lon, date):
    return _get_setting_time(
        lat, lon, date, _SUN, _CIVIL_HORIZON, use_center=True)


def get_nautical_dawn_time(lat, lon, date):
    return _get_rising_time(
        lat, lon, date, _SUN, _NAUTICAL_HORIZON, use_center=True)


def get_nautical_dusk_time(lat, lon, date):
    return _get_setting_time(
        lat, lon, date, _SUN, _NAUTICAL_HORIZON, use_center=True)


def get_astronomical_dawn_time(lat, lon, date):
    return _get_rising_time(
        lat, lon, date, _SUN, _ASTRONOMICAL_HORIZON, use_center=True)
    
    
def get_astronomical_dusk_time(lat, lon, date):
    return _get_setting_time(
        lat, lon, date, _SUN, _ASTRONOMICAL_HORIZON, use_center=True)
    
    
def _get_rising_time(lat, lon, date, body, horizon, use_center=False):
    method = ephem.Observer.next_rising
    return _get_time(method, lat, lon, date, body, horizon, use_center)


def _get_time(method, lat, lon, date, body, horizon, use_center):
    
    observer = _create_observer(lat, lon, horizon)

    midnight = _get_midnight_as_ephem_date(lon, date)
    
    try:
        ephem_date = method(
            observer, body, start=midnight, use_center=use_center)
    except ephem.CircumpolarError:
        return None
    else:
        return _get_datetime_from_ephem_date(ephem_date)
    
    
def _create_observer(lat, lon, horizon):
    observer = ephem.Observer()
    observer.lat = math.radians(lat)
    observer.lon = math.radians(lon)
    observer.horizon = horizon
    observer.pressure = 0
    return observer


def _get_midnight_as_ephem_date(lon, date):
    dt = datetime.datetime(date.year, date.month, date.day)
    dt -= datetime.timedelta(hours=lon * 24. / 360.)
    dt = pytz.utc.localize(dt)
    return dt.strftime('%Y/%m/%d %H:%M:%S')
    

def _get_datetime_from_ephem_date(ephem_date):
    year, month, day, hour, minute, float_second = ephem_date.tuple()
    second = int(math.floor(float_second))
    microsecond = int(round(1000000 * (float_second - second)))
    return datetime.datetime(
        year, month, day, hour, minute, second, microsecond, pytz.utc)


def _get_setting_time(lat, lon, date, body, horizon, use_center=False):
    method = ephem.Observer.next_setting
    return _get_time(method, lat, lon, date, body, horizon, use_center)


def get_moon_altitude(lat, lon, time):
    moon = _create_moon(lat, lon, time)
    return math.degrees(float(moon.alt))


def _create_moon(lat, lon, time):
    observer = ephem.Observer()
    observer.lat = math.radians(lat)
    observer.lon = math.radians(lon)
    observer.pressure = 0
    observer.date = time
    return ephem.Moon(observer)


def get_moon_illumination(lat, lon, time):
    moon = _create_moon(lat, lon, time)
    return moon.phase
