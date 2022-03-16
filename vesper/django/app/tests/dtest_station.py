import datetime

from django.test import TestCase
import pytz

from vesper.django.app.models import Station


class StationTests(TestCase):
    
    
    def setUp(self):
        self.station = \
            Station.objects.create(name='Test', time_zone='US/Eastern')
        self.tz = self.station.tz
        
        
    def test_local_to_utc(self):
        
        cases = [
            ((2016, 8, 23), None, (2016, 8, 23, 4)),
            ((2016, 8, 23), self.tz, (2016, 8, 23, 4)),
            ((2015, 12, 31, 22, 12, 34), None, (2016, 1, 1, 3, 12, 34)),
            ((2015, 12, 31, 22, 12, 34), self.tz, (2016, 1, 1, 3, 12, 34))
        ]
        
        for args, tz, expected in cases:
            dt = datetime.datetime(*args)
            if tz is not None:
                dt = tz.localize(dt)
            result = self.station.local_to_utc(dt)
            expected = datetime.datetime(*expected, tzinfo=pytz.utc)
            self.assertEqual(result, expected)


    def test_utc_to_local(self):
          
        cases = [
            ((2016, 8, 23, 4), False, (2016, 8, 23)),
            ((2016, 1, 1, 3, 12, 34), True, (2015, 12, 31, 22, 12, 34))
        ]
          
        for args, set_tzinfo, expected in cases:
            tz = pytz.utc if set_tzinfo else None
            dt = datetime.datetime(*args, tzinfo=tz)
            result = self.station.utc_to_local(dt)
            expected = self.tz.localize(datetime.datetime(*expected))
            self.assertEqual(result, expected)
            
            
    def test_get_midnight_utc(self):
        
        cases = [
            ((2016, 8, 23), (2016, 8, 23, 4))
        ]
        
        self._test_get_time_utc(cases, self.station.get_midnight_utc)
        
        
    def _test_get_time_utc(self, cases, get_time_utc):
        for args, expected in cases:
            date = datetime.date(*args)
            result = get_time_utc(date)
            expected = datetime.datetime(*expected, tzinfo=pytz.utc)
            self.assertEqual(result, expected)
            
            
    def test_get_noon_utc(self):
        
        cases = [
            ((2016, 8, 23), (2016, 8, 23, 16))
        ]
        
        self._test_get_time_utc(cases, self.station.get_noon_utc)
            
            
    def test_get_day_interval_utc(self):
        
        cases = [
            (((2016, 8, 23),), ((2016, 8, 23, 4), (2016, 8, 24, 4))),
            (((2016, 8, 23), (2016, 9, 1)), ((2016, 8, 23, 4), (2016, 9, 2, 4)))
        ]
        
        self._test_get_interval_utc(cases, self.station.get_day_interval_utc)
        
        
    def _test_get_interval_utc(self, cases, get_interval_utc):
        for args, expected in cases:
            args = tuple(datetime.date(*a) for a in args)
            result = get_interval_utc(*args)
            expected = tuple(
                datetime.datetime(*e, tzinfo=pytz.utc) for e in expected)
            self.assertEqual(result, expected)
        
 
    def test_get_night_interval_utc(self):
        
        cases = [
            (((2016, 8, 23),), ((2016, 8, 23, 16), (2016, 8, 24, 16))),
            (((2016, 8, 23), (2016, 9, 1)),
                ((2016, 8, 23, 16), (2016, 9, 2, 16)))
        ]
        
        self._test_get_interval_utc(cases, self.station.get_night_interval_utc)
        
        
    def test_get_day(self):
        
        cases = [
            ((2017, 4, 10, 16), (2017, 4, 10)),
            ((2017, 4, 10, 3, 59, 59), (2017, 4, 9)),
            ((2017, 4, 10, 4), (2017, 4, 10))
        ]
        
        self._test_get_date(cases, self.station.get_day)
        
        
    def _test_get_date(self, cases, get_date):
        for dt, expected in cases:
            dt = datetime.datetime(*dt)
            expected = datetime.date(*expected)
            result = get_date(dt)
            self.assertEqual(result, expected)


    def test_get_night(self):
        
        cases = [
            ((2017, 4, 10, 4), (2017, 4, 9)),
            ((2017, 4, 10, 15, 59, 59), (2017, 4, 9)),
            ((2017, 4, 10, 16), (2017, 4, 10))
        ]
        
        self._test_get_date(cases, self.station.get_night)
        
        
