import datetime

import pytz

import vesper.util.time_utils as time_utils

from test_case import TestCase


_DT = datetime.datetime
_D = datetime.date
_T = datetime.time
_TD = datetime.timedelta

_D2 = '{:02d}'.format
_D4 = '{:04d}'.format
_D6 = '{:06d}'.format


def _get_four_digit_year(y):
    if y < 100:
        return y + (2000 if y < 50 else 1900)
    else:
        return y
    
    
def _create_utc_datetime(y, M, d, h, m, s, u, delta):
    dt = _DT(y, M, d, h, m, s, u, pytz.utc)
    return dt + _TD(hours=delta)


_TIME_ROUNDING_CASES = [
    ((0, 0, 0, 0, 1), (0, 0, 0)),
    ((0, 0, 0, 1, 1), (0, 0, 0)),
    ((0, 0, 0, 999999, 1), (0, 0, 1)),
    ((0, 0, 59, 999999, 60), (0, 1, 0)),
    ((0, 1, 2, 3, 60), (0, 1, 0)),
    ((0, 59, 59, 999999, 3600), (1, 0, 0)),
    ((1, 2, 3, 4, 3600), (1, 0, 0)),
    ((0, 4, 59, 999999, 300), (0, 5, 0)),
    ((0, 5, 1, 2, 300), (0, 5, 0)),
    ((12, 23, 45, 0, 30), (12, 24, 0)),
    ((12, 23, 45, 0, 1200), (12, 20, 0)),
    ((13, 34, 56, 0, 7200), (14, 0, 0))
]


_BAD_TIME_ROUNDING_UNIT_SIZES = [-1, 0, .5, 7]


class TimeUtilsTests(TestCase):
    
    
    def test_create_utc_datetime(self):
        
        eastern = pytz.timezone('US/Eastern')
        
        cases = [
            (2015, 5, 24, 12, 0, 0, 0, None, None, 0),
            (2015, 5, 24, 12, 0, 0, 0, 'US/Eastern', None, 4),
            (2015, 5, 24, 22, 0, 0, 0, 'US/Eastern', None, 4),
            (2014, 12, 31, 22, 0, 0, 0, 'US/Eastern', None, 5),
            (2015, 3, 8, 1, 59, 59, 999999, 'US/Eastern', None, 5),
            (2015, 3, 8, 3, 0, 0, 0, eastern, None, 4),
            (2015, 11, 1, 1, 0, 0, 0, eastern, True, 4),
            (2015, 11, 1, 1, 0, 0, 0, eastern, False, 5),
            (2015, 11, 1, 2, 0, 0, 0, eastern, None, 5)
        ]
        
        for y, M, d, h, m, s, u, z, is_dst, delta in cases:
            expected = _create_utc_datetime(y, M, d, h, m, s, u, delta)
            result = time_utils.create_utc_datetime(
                y, M, d, h, m, s, u, z, is_dst)
            self.assertEqual(result, expected)
            
        
    def test_create_utc_datetime_errors(self):
        
        cases = [
            (2015, 4, 24, 0, 'Bobo'),
            (2015, 3, 8, 2, 'US/Eastern'),
            (2015, 11, 1, 1, 'US/Eastern')
        ]
        
        f = time_utils.create_utc_datetime
        
        for y, m, d, h, z in cases:
            self._assert_raises(ValueError, f, y, m, d, h, time_zone=z)
            
            
    def test_parse_date_time(self):
        
        cases = [
                 
            (1900, 1, 1, 0, 0, 0, 0),
            (2099, 12, 31, 23, 59, 59, 999999),
            (2015, 4, 23, 10, 12, 34, 500000),
            
            (00, 1, 1, 0, 0, 0, 0),
            (99, 12, 31, 23, 59, 59, 999999),
            (15, 4, 23, 10, 12, 34, 500000),
            
        ]
        
        for y, M, d, h, m, s, f in cases:
            year = _get_four_digit_year(y)
            expected_result = _DT(year, M, d, h, m, s, f)
            format_ = _D2 if y < 100 else _D4
            y = format_(y)
            M = _D2(M)
            d = _D2(d)
            h = _D2(h)
            m = _D2(m)
            s = _D2(s)
            f = _D6(f)
            result = time_utils.parse_date_time(y, M, d, h, m, s, f)
            self.assertEqual(result, expected_result)
            
            
    def test_parse_date_time_errors(self):
        
        cases = [
                 
            # year out of range
            (0, 1, 1, 0, 0, 0, 0),
            (1899, 12, 31, 0, 0, 0, 0),
            (2100, 1, 1, 0, 0, 0, 0),
            
            # month out of range
            (2015, 0, 1, 0, 0, 0, 0),
            (2015, 13, 1, 0, 0, 0, 0),
            
            # day out of range
            (2015, 1, 0, 0, 0, 0, 0),
            (2015, 1, 32, 0, 0, 0, 0),
            (2015, 2, 29, 0, 0, 0, 0),
            
            # hour out of range
            (2015, 1, 1, 24, 0, 0, 0),
            
            # minute out of range
            (2015, 1, 1, 0, 60, 0, 0),
            
            # second out of range
            (2015, 1, 1, 0, 0, 60, 0),
            
        ]
        
        for y, M, d, h, m, s, f in cases:
            y = _D4(y)
            M = _D2(M)
            d = _D2(d)
            h = _D2(h)
            m = _D2(m)
            s = _D2(s)
            f = _D6(f)
            self._assert_raises(
                ValueError, time_utils.parse_date_time, y, M, d, h, m, s, f)
            
            
    def test_parse_date(self):
        
        cases = [
                 
            (1900, 1, 1),
            (2099, 12, 31),
            (2014, 1, 2),
            (2014, 2, 28),
            (2012, 2, 29),
            
            (0, 1, 1),
            (99, 12, 31),
            (50, 1, 1),
            (49, 12, 31)
            
        ]
        
        for y, m, d in cases:
            year = _get_four_digit_year(y)
            expected_result = _D(year, m, d)
            format_ = _D2 if y < 100 else _D4
            y = format_(y)
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
                expected_result = _T(h, m, s, u)
                result = time_utils.parse_time(_D2(h), _D2(m), _D2(s), str(f))
                 
            elif len(case) == 3:
                h, m, s = case
                expected_result = _T(h, m, s)
                result = time_utils.parse_time(_D2(h), _D2(m), _D2(s))
                 
            else:
                h, m = case
                expected_result = _T(h, m)
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
            (123, 45, 6),
             
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
                expected_result = _TD(
                    hours=h, minutes=m, seconds=s, microseconds=u)
                result = time_utils.parse_time_delta(
                    str(h), _D2(m), _D2(s), str(f))
                 
            elif len(case) == 3:
                h, m, s = case
                expected_result = _TD(hours=h, minutes=m, seconds=s)
                result = time_utils.parse_time_delta(str(h), _D2(m), _D2(s))
                 
            else:
                h, m = case
                expected_result = _TD(hours=h, minutes=m)
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


    def test_round_datetime(self):
        
        for (h, m, s, u, unit_size), (eh, em, es) in _TIME_ROUNDING_CASES:
            dt = _DT(2015, 8, 14, h, m, s, u)
            r = time_utils.round_datetime(dt, unit_size)
            edt = _DT(2015, 8, 14, eh, em, es)
            self.assertEqual(r, edt)
            
        # case that rounds to the beginning of the next day
        dt = _DT(2015, 8, 31, 23, 59)
        r = time_utils.round_datetime(dt, 900)
        edt = _DT(2015, 9, 1)
        self.assertEqual(r, edt)
        
        # case with an aware `datetime`
        localize = pytz.utc.localize
        dt = localize(_DT(2015, 8, 14, 1, 1))
        r = time_utils.round_datetime(dt, 3600)
        edt = localize(_DT(2015, 8, 14, 1))
        self.assertEqual(r, edt)
        
        
    def test_round_datetime_errors(self):
        for unit_size in _BAD_TIME_ROUNDING_UNIT_SIZES:
            dt = _DT(2015, 8, 14)
            self._assert_raises(
                ValueError, time_utils.round_datetime, dt, unit_size)
        
        
    def test_round_time(self):
        
        for (h, m, s, u, unit_size), (eh, em, es) in _TIME_ROUNDING_CASES:
            time = _T(h, m, s, u)
            result = time_utils.round_time(time, unit_size)
            expected = _T(eh, em, es)
            self.assertEqual(result, expected)
            
        # case that rounds up to midnight
        time = _T(23, 59)
        result = time_utils.round_time(time, 900)
        expected = _T()
        self.assertEqual(result, expected)
        
        
    def test_round_time_errors(self):
        for unit_size in _BAD_TIME_ROUNDING_UNIT_SIZES:
            time = _T()
            self._assert_raises(
                ValueError, time_utils.round_time, time, unit_size)
        
        
def _tuplize(x):
    return x if isinstance(x, tuple) else (x,)
