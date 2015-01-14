from __future__ import print_function

import datetime

import pytz

from old_bird.archiver_time_keeper import (
    ArchiverTimeKeeper, NonexistentTimeError, AmbiguousTimeError)
from vesper.archive.station import Station

from test_case import TestCase


_STATIONS = [
    ('A', 'US/Eastern'),
    ('B', 'America/Mexico_City'),
    ('C', 'US/Arizona')
]

_MONITORING_TIME_ZONES = {
    'C': 'UTC'
}

_MONITORING_START_TIMES = {
    2012: {'A': ('12:34:56', ['10-1']), 'B': ('21:00:00', ['9-1', '10-31'])},
    2013: {'A': ('19:00:00', []), 'B': ('22:00:00', ['8-1', ('9-1', '11-30')])}
}


class ArchiverTimeKeeperTests(TestCase):
    
               
    def setUp(self):
        stations = self._create_stations(_STATIONS)
        self.time_keeper = ArchiverTimeKeeper(
            stations, _MONITORING_TIME_ZONES, _MONITORING_START_TIMES)
            
            
    def _create_stations(self, tuples):
        return dict(self._create_stations_item(*t) for t in tuples)
    
    
    def _create_stations_item(self, station_name, time_zone_name):
        station = Station(station_name, station_name, time_zone_name)
        return (station_name, station)
                
        
    def test_convert_naive_time_to_utc(self):
        
        cases = [
                 
            # A is US/Eastern
            ('A', '2012-01-01 00:00:00', '2012-01-01 05:00:00'),
            ('A', '2012-03-11 01:59:59', '2012-03-11 06:59:59'),
            ('A', '2012-03-11 03:00:00', '2012-03-11 07:00:00'),
            ('A', '2012-07-01 22:00:00', '2012-07-02 02:00:00'),
            ('A', '2012-11-04 00:59:59', '2012-11-04 04:59:59'),
            ('A', '2012-11-04 02:00:00', '2012-11-04 07:00:00'),
            ('A', '2012-12-31 22:00:00', '2013-01-01 03:00:00'),
            
            # B is America/Mexico_City
            ('B', '2013-01-01 00:00:00', '2013-01-01 06:00:00'),
            ('B', '2013-04-07 01:59:59', '2013-04-07 07:59:59'),
            ('B', '2013-04-07 03:00:00', '2013-04-07 08:00:00'),
            ('B', '2013-07-01 22:00:00', '2013-07-02 03:00:00'),
            ('B', '2013-10-27 00:59:59', '2013-10-27 05:59:59'),
            ('B', '2013-10-27 02:00:00', '2013-10-27 08:00:00'),
            ('B', '2013-12-31 22:00:00', '2014-01-01 04:00:00'),
            
            # C is UTC
            ('C', '2014-01-01 00:00:00', '2014-01-01 00:00:00'),
            ('C', '2014-07-01 00:00:00', '2014-07-01 00:00:00'),
            ('C', '2014-12-31 00:00:00', '2014-12-31 00:00:00')
            
        ]
        
        convert = self.time_keeper.convert_naive_time_to_utc
        
        for station_name, time, expected_result in cases:
            
            time = _parse_naive_date_time(time)
            result = convert(time, station_name)
            
            expected_result = _parse_naive_date_time(expected_result)
            expected_result = pytz.utc.localize(expected_result)
            
            self.assertEqual(result, expected_result)
            
            
    def test_convert_naive_time_to_utc_errors(self):
        
        nonexistent = [
                       
            ('A', '2012-03-11 02:00:00'),
            ('A', '2012-03-11 02:30:00'),
            ('A', '2012-03-11 02:59:59'),
            
            ('B', '2013-04-07 02:00:00'),
            ('B', '2013-04-07 02:30:00'),
            ('B', '2013-04-07 02:59:59')
            
        ]
        
        ambiguous = [
                     
            ('A', '2012-11-04 01:00:00'),
            ('A', '2012-11-04 01:30:00'),
            ('A', '2012-11-04 01:59:59'),
            
            ('B', '2013-10-27 01:00:00'),
            ('B', '2013-10-27 01:30:00'),
            ('B', '2013-10-27 01:59:59')
            
        ]
        
        self._test_convert_naive_time_to_utc_errors(
            nonexistent, NonexistentTimeError)
        
        self._test_convert_naive_time_to_utc_errors(
            ambiguous, AmbiguousTimeError)
                
        
    def _test_convert_naive_time_to_utc_errors(self, cases, exceptionClass):
        
        convert = self.time_keeper.convert_naive_time_to_utc
        
        for station_name, time in cases:
            time = _parse_naive_date_time(time)
            self._assert_raises(exceptionClass, convert, time, station_name)
            
            
    def test_convert_elapsed_time_to_utc(self):
         
        cases = [
            ('B', '2012-08-31', '1:23:45', None),
            ('B', '2012-09-01', '1:23:45', '2012-09-02 03:23:45'),
            ('B', '2013-11-15', '4:23:45', '2013-11-16 08:23:45')
        ]
         
        for station_name, night, time_delta, expected_result in cases:
            
            night = _parse_date(night)
            time_delta = _parse_time_delta(time_delta)
            
            if expected_result is not None:
                expected_result = _parse_naive_date_time(expected_result)
                expected_result = pytz.utc.localize(expected_result)
                
            method = self.time_keeper.convert_elapsed_time_to_utc
            result = method(time_delta, station_name, night)
            
            self.assertEqual(result, expected_result)
             
             
_combine = datetime.datetime.combine


def _parse_naive_date_time(time):
    if time is None:
        return None
    else:
        date, time = time.split()
        date = _parse_date(date)
        time = _parse_time(time)
        return _combine(date, time)


def _parse_date(date):
    if date is None:
        return None
    else:
        return datetime.date(*[int(s) for s in date.split('-')])


def _parse_time(time):
    if time is None:
        return None
    else:
        return datetime.time(*[int(s) for s in time.split(':')])


def _parse_time_delta(delta):
    if delta is None:
        return None
    else:
        hours, minutes, seconds = delta.split(':')
        return datetime.timedelta(
            hours=int(hours), minutes=int(minutes), seconds=int(seconds))
