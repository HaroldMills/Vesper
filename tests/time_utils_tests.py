import unittest

import nfc.util.time_utils as time_utils


class TimeUtilsTests(unittest.TestCase):
    
    
    def test_check_year(self):
        good = [1900, 2000, 2099]
        bad = [1800, 1899, 2100, 2200]
        self._test(good, bad, time_utils.check_year)
        
        
    def _test(self, good, bad, function):
        for case in good:
            function(*_tuplize(case))
        for case in bad:
            self._assert_raises(ValueError, function, *_tuplize(case))
            
            
    def _assert_raises(self, exception_class, function, *args, **kwargs):
        
        self.assertRaises(exception_class, function, *args, **kwargs)
        
        try:
            function(*args, **kwargs)
            
        except exception_class, e:
            print str(e)
            
            
    def test_check_month(self):
        good = range(1, 13)
        bad = [-1, 0, 13, 14]
        self._test(good, bad, time_utils.check_month)
        
        
    def test_check_day(self):
        good = [(1, 2012, 1), (31, 2012, 1), (29, 2012, 2), (30, 2012, 4)]
        bad = [(0, 2012, 1), (32, 2012, 1), (30, 2012, 2), (31, 2012, 4)]
        self._test(good, bad, time_utils.check_day)
        
        
    def test_check_hour(self):
        good = range(0, 24)
        bad = [-2, -1, 24, 25]
        self._test(good, bad, time_utils.check_hour)
        
        
    def test_check_minute(self):
        self._test_ms(time_utils.check_minute)
        
        
    def _test_ms(self, function):
        good = range(0, 60)
        bad = [-2, -1, 60, 61]
        self._test(good, bad, function)
        
        
    def test_check_minutes(self):
        self._test_ms(time_utils.check_minutes)
        
        
    def test_check_second(self):
        self._test_ms(time_utils.check_second)
        
        
    def test_check_seconds(self):
        self._test_ms(time_utils.check_seconds)


def _tuplize(x):
    return x if isinstance(x, tuple) else (x,)
