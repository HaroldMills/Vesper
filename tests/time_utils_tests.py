import datetime

import vesper.util.time_utils as time_utils

from test_case import TestCase


_D2 = '{:2d}'.format
_D4 = '{:4d}'.format


class TimeUtilsTests(TestCase):
    
    
    def test_parse_date(self):
        
        cases = [
                 
            (1900, 01, 01),
            (2099, 12, 31),
            (2014, 01, 02),
            (2014, 02, 28),
            (2012, 02, 29),
            
            (00, 01, 01),
            (99, 12, 31),
            (50, 1, 1),
            (49, 12, 31)
            
        ]
        
        for y, m, d in cases:
            year = y
            if y < 100:
                year += 2000 if y < 50 else 1900
            expected_result = datetime.date(year, m, d)
            f = _D2 if y < 100 else _D4
            y = f(y)
            m = _D2(m)
            d = _D2(d)
            result = time_utils.parse_date(y, m, d)
            self.assertEqual(result, expected_result)
            
            
    def test_parse_date_errors(self):
        
        cases = [
                 
            # year out of range
            (1899, 12, 31),
            (2100, 1, 1),
            
            # month out of range
            (2015, 0, 1),
            (2015, 13, 1),
            
            # day out of range
            (2015, 1, 0),
            (2015, 1, 32),
            (2015, 2, 29)
            
        ]
        
        for y, m, d in cases:
            y = _D4(y)
            m = _D2(m)
            d = _D2(d)
            self._assert_raises(ValueError, time_utils.parse_date, y, m, d)
            
            
    def test_parse_fractional_second(self):
        
        cases = [
                 
            # six or fewer digits, starting with nonzero digit
            ('1', 100000),
            ('12', 120000),
            ('123', 123000),
            ('1234', 123400),
            ('12345', 123450),
            ('123456', 123456),
            
            # six or fewer digits, starting with zero
            ('01', 10000),
            ('001', 1000),

            # more than six digits
            ('1234561', 123456),
            ('1234567', 123457),
            ('12345678901234567890', 123457),
            ('0000001', 0),
            ('0000009', 1),
            ('00000009', 0)
            
        ]
        
        parse = time_utils._parse_fractional_second
        for digits, expected in cases:
            self.assertEqual(parse(digits), expected)
            
            
    def test_parse_time(self):
          
        cases = [
                 
            # including fractional second
            (0, 0, 0, 0),
            (12, 3, 4, 5),
            (12, 34, 56, 1),
            (12, 34, 56, 12),
            (12, 34, 56, 123),
            (12, 34, 56, 1234),
            (12, 34, 56, 12345),
            (12, 34, 56, 123456),
            (12, 34, 56, 1234561),
            (12, 34, 56, 1234567),
            
            # including extra zeros in fractional second
            (0, 0, 0, '000'),
            (0, 0, 0, '500'),
            (0, 0, 0, '500000000'),
            
            # including second but not fractional second
            (0, 0, 0),
            (12, 3, 4),
            (12, 34, 56),
            (23, 59, 59),
             
            # excluding second
            (0, 0),
            (12, 3),
            (12, 34),
            (23, 59)
              
        ]
          
        for case in cases:
             
            if len(case) == 4:
                h, m, s, f = case
                u = time_utils._parse_fractional_second(str(f))
                expected_result = datetime.time(h, m, s, u)
                result = time_utils.parse_time(_D2(h), _D2(m), _D2(s), str(f))
                 
            elif len(case) == 3:
                h, m, s = case
                expected_result = datetime.time(h, m, s)
                result = time_utils.parse_time(_D2(h), _D2(m), _D2(s))
                 
            else:
                h, m = case
                expected_result = datetime.time(h, m)
                result = time_utils.parse_time(_D2(h), _D2(m))
                
            self.assertEqual(result, expected_result)
                 
            
    def test_parse_time_errors(self):
        
        cases = [
                 
            # hour out of range
            (24, 0, 0),
            
            # minute out of range
            (1, 60, 0),
            
            # second out of range
            (1, 1, 60)
            
        ]
        
        for h, m, s in cases:
            h = _D2(h)
            m = _D2(m)
            s = _D2(s)
            self._assert_raises(ValueError, time_utils.parse_time, h, m, s)
            
            
    def test_parse_time_delta(self):
          
        cases = [
                 
            # including fractional second
            (0, 0, 0, 0),
            (12, 3, 4, 5),
            (12, 34, 56, 1),
            (12, 34, 56, 12),
            (12, 34, 56, 123),
            (12, 34, 56, 1234),
            (12, 34, 56, 12345),
            (12, 34, 56, 123456),
            (12, 34, 56, 1234561),
            (12, 34, 56, 1234567),
            
            # including extra zeros in fractional second
            (0, 0, 0, '000'),
            (0, 0, 0, '500'),
            (0, 0, 0, '500000000'),
            
            # including second but not fractional second
            (0, 0, 0),
            (12, 3, 4),
            (12, 34, 56),
            (123, 45, 06),
             
            # excluding second
            (0, 0),
            (12, 3),
            (12, 34),
            (123, 45)
              
        ]
          
        for case in cases:
             
            if len(case) == 4:
                h, m, s, f = case
                u = time_utils._parse_fractional_second(str(f))
                expected_result = datetime.timedelta(
                    hours=h, minutes=m, seconds=s, microseconds=u)
                result = time_utils.parse_time_delta(
                    str(h), _D2(m), _D2(s), str(f))
                 
            elif len(case) == 3:
                h, m, s = case
                expected_result = datetime.timedelta(
                    hours=h, minutes=m, seconds=s)
                result = time_utils.parse_time_delta(str(h), _D2(m), _D2(s))
                 
            else:
                h, m = case
                expected_result = datetime.timedelta(hours=h, minutes=m)
                result = time_utils.parse_time_delta(str(h), _D2(m))
                
            self.assertEqual(result, expected_result)
                 
            
    def test_parse_time_delta_errors(self):
        
        cases = [
                 
            # minutes out of range
            (1, 60, 0),
            
            # seconds out of range
            (1, 1, 60)
            
        ]
        
        for h, m, s in cases:
            h = str(h)
            m = _D2(m)
            s = _D2(s)
            self._assert_raises(
                ValueError, time_utils.parse_time_delta, h, m, s)
            
            
    def test_parse_command_line_date(self):
        
        cases = [
            (1900, 01, 01),
            (2099, 12, 31),
            (2014, 01, 02),
            (2014, 02, 28),
            (2012, 02, 29)
        ]
        
        for y, m, d in cases:
            s = '{:d}-{:02d}-{:02d}'.format(y, m, d)
            expected_result = datetime.date(y, m, d)
            result = time_utils.parse_command_line_date(s)
            self.assertEqual(result, expected_result)
            
            
    def test_parse_command_line_date_errors(self):
        
        cases = [
                 
            # bad characters
            'bobo',
            
            # wrong numbers of digits
            '1-01-01',
            '12345-01-01',
            '2014-1-01',
            '2014-123-01',
            '2014-01-1',
            '2014-01-123',
            
            # values out of range
            '1899-12-31',
            '2100-01-01',
            '2014-00-01',
            '2014-13-01',
            '2014-01-00',
            '2014-01-32',
            '2014-02-29'
            
        ]
        
        for case in cases:
            self._assert_raises(
                ValueError, time_utils.parse_command_line_date, case)
            
            
    def test_check_year(self):
        good = [1900, 2000, 2099]
        bad = [1800, 1899, 2100, 2200]
        self._test(good, bad, time_utils.check_year)
        
        
    def _test(self, good, bad, function):
        for case in good:
            function(*_tuplize(case))
        for case in bad:
            self._assert_raises(ValueError, function, *_tuplize(case))
            
            
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
