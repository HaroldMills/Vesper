import datetime
import unittest

import pytz

from vesper.archive.station import Station


STATION_TUPLE = ('Ithaca', 'Test Station', 'US/Eastern')


class StationTests(unittest.TestCase):
    
    
    def setUp(self):
        self.station = Station(*STATION_TUPLE)
        
        
    def test_initializer(self):
        name, long_name, time_zone_name = STATION_TUPLE
        s = self.station
        self.assertEqual(s.name, name)
        self.assertEqual(s.long_name, long_name)
        self.assertEqual(s.time_zone.zone, time_zone_name)
        
        
    def test_get_night(self):
        
        dt = datetime.datetime
        d = datetime.date
        
        eastern = pytz.timezone('US/Eastern')
        utc = pytz.utc
        
        cases = [
                 
            # naive times
            (dt(2012, 1, 1), d(2011, 12, 31)),
            (dt(2012, 1, 1, 11, 59, 59), d(2011, 12, 31)),
            (dt(2012, 1, 1, 12), d(2012, 1, 1)),
            
            # aware local time
            (dt(2012, 1, 1, tzinfo=eastern), d(2011, 12, 31)),
            
            # aware UTC time
            (dt(2012, 1, 1, tzinfo=utc), d(2011, 12, 31)),
            (dt(2012, 1, 1, 16, 59, 59, tzinfo=utc), d(2011, 12, 31)),
            (dt(2012, 1, 1, 17, tzinfo=utc), d(2012, 1, 1))
            
        ]
        
        get_night = self.station.get_night
        
        for time, date in cases:
            self.assertEqual(get_night(time), date)
