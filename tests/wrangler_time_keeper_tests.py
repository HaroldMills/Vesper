import datetime
import unittest

from old_bird.wrangler_time_keeper import WranglerTimeKeeper


_DEFAULT_DST_INTERVALS = {
    2012: ('3-11 2:00:00', '11-4 2:00:00'),
    2013: ('3-10 2:00:00', '11-3 2:00:00')
}
  
_DST_INTERVALS = {
    2012: {'B': None, 'C': ('3-12 2:00:00', '11-3 12:34:56')},
    2013: {'C': None}
}
  
_MONITORING_START_TIMES = {
    2012: {'A': ('12:34:56', ['10-1']), 'B': ('21:00:00', ['9-1', '10-31'])},
    2013: {'A': ('19:00:00', []), 'B': ('22:00:00', ['8-1', ('9-1', '10-31')])}
}


class WranglerTimeKeeperTests(unittest.TestCase):
    
               
    def setUp(self):
        self.time_keeper = WranglerTimeKeeper(
            _DEFAULT_DST_INTERVALS, _DST_INTERVALS, _MONITORING_START_TIMES)
            
            
    def test_is_time_ambiguous(self):
        
        cases = [
                 
            # A observes regular DST
            ('A', '2012-01-01 00:00:00', False),
            ('A', '2012-03-11 02:00:00', False),    # no such local time
            ('A', '2012-03-11 03:00:00', False),
            ('A', '2012-07-01 00:00:00', False),
            ('A', '2012-11-04 00:59:59', False),
            ('A', '2012-11-04 01:00:00', True),
            ('A', '2012-11-04 01:30:00', True),
            ('A', '2012-11-04 01:59:59', True),
            ('A', '2012-11-04 02:00:00', False),
            ('A', '2012-12-31 23:59:59', False),
            ('A', '2013-11-03 00:59:59', False),
            ('A', '2013-11-03 01:00:00', True),
            ('A', '2013-11-03 01:30:00', True),
            ('A', '2013-11-03 01:59:59', True),
            ('A', '2013-11-03 02:00:00', False),
             
            # B does not observe DST for 2012, but does for 2013
            ('B', '2012-01-01 00:00:00', False),
            ('B', '2012-03-11 02:00:00', False),    # no such local time
            ('B', '2012-03-11 03:00:00', False),
            ('B', '2012-07-01 00:00:00', False),
            ('B', '2012-11-04 00:59:59', False),
            ('B', '2012-11-04 01:00:00', False),
            ('B', '2012-11-04 01:30:00', False),
            ('B', '2012-11-04 01:59:59', False),
            ('B', '2012-11-04 02:00:00', False),
            ('B', '2012-12-31 23:59:59', False),
            ('B', '2013-11-03 00:59:59', False),
            ('B', '2013-11-03 01:00:00', True),
            ('B', '2013-11-03 01:30:00', True),
            ('B', '2013-11-03 01:59:59', True),
            ('B', '2013-11-03 02:00:00', False),
             
            # C observes custom DST for 2012, but none for 2013
            ('C', '2012-01-01 00:00:00', False),
            ('C', '2012-03-10 02:00:00', False),    # no such local time
            ('C', '2012-03-10 03:00:00', False),
            ('C', '2012-07-01 00:00:00', False),
            ('C', '2012-11-03 11:34:55', False),
            ('C', '2012-11-03 11:34:56', True),
            ('C', '2012-11-03 12:04:56', True),
            ('C', '2012-11-03 12:34:55', True),
            ('C', '2012-11-03 12:34:56', False),
            ('C', '2012-12-31 23:59:59', False),
            ('C', '2013-11-03 00:59:59', False),
            ('C', '2013-11-03 01:00:00', False),
            ('C', '2013-11-03 01:30:00', False),
            ('C', '2013-11-03 01:59:59', False),
            ('C', '2013-11-03 02:00:00', False),
            
        ]
        
        for station_name, time, expected_result in cases:
            time = _parse_date_time(time)
            result = self.time_keeper.is_time_ambiguous(time, station_name)
            self.assertEqual(result, expected_result)
            
            
    def test_is_time_ambiguous_errors(self):
        method = self.time_keeper.is_time_ambiguous
        for year in [2011, 2014]:
            time = datetime.datetime(year, 1, 1)
            self._assert_raises(ValueError, method, time, 'A')
        
        
    def test_get_monitoring_start_time(self):
         
        cases = [
                 
            ('A', '2012-09-30', None),
            ('A', '2012-10-01', '12:34:56'),
            ('A', '2012-10-02', None),
            ('A', '2013-01-01', '19:00:00'),
            ('A', '2013-06-01', '19:00:00'),
            ('A', '2013-12-31', '19:00:00'),
            ('A', '2014-09-01', None),
            
            ('B', '2012-01-01', None),
            ('B', '2012-06-01', None),
            ('B', '2012-08-31', None),
            ('B', '2012-09-01', '21:00:00'),
            ('B', '2012-09-02', None),
            ('B', '2012-10-30', None),
            ('B', '2012-10-31', '21:00:00'),
            ('B', '2012-11-01', None),
            ('B', '2012-12-31', None),
            ('B', '2013-07-31', None),
            ('B', '2013-08-01', '22:00:00'),
            ('B', '2013-08-02', None),
            ('B', '2013-08-31', None),
            ('B', '2013-09-01', '22:00:00'),
            ('B', '2013-10-01', '22:00:00'),
            ('B', '2013-10-31', '22:00:00'),
            ('B', '2013-11-01', None),
            
            ('C', '2012-09-01', None)
            
        ]
        
        for station_name, night, expected_result in cases:
            night = _parse_date(night)
            if expected_result is not None:
                time = _parse_time(expected_result)
                expected_result = _combine(night, time)
            method = self.time_keeper.get_monitoring_start_time
            result = method(station_name, night)
            self.assertEqual(result, expected_result)
            
            
    def test_resolve_elapsed_time(self):
        
        cases = [
            ('B', '2012-08-31', '1:23:45', None),
            ('B', '2012-09-01', '1:23:45', '2012-09-01 22:23:45'),
            ('B', '2012-09-01', '4:23:45', '2012-09-02 01:23:45')
        ]
        
        for station_name, night, time_delta, expected_result in cases:
            night = _parse_date(night)
            time_delta = _parse_time_delta(time_delta)
            expected_result = _parse_date_time(expected_result)
            method = self.time_keeper.resolve_elapsed_time
            result = method(station_name, night, time_delta)
            self.assertEqual(result, expected_result)
            
            
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class, e:
            print str(e)


_combine = datetime.datetime.combine


def _parse_date_time(time):
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
