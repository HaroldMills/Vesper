import datetime

from vesper.tests.test_case import TestCase
from vesper.util.calendar_month import CalendarMonth as CM


_2016_5 = CM(2016, 5)
_2016_5_ = CM(2016, 5)
_2016_6 = CM(2016, 6)
_2016_7 = CM(2016, 7)
_2020_7 = CM(2020, 7)


class CalendarMonthTests(TestCase):
    
    
    def test_from_date(self):
        d = datetime.date(2016, 5, 1)
        m = CM.from_date(d)
        self.assertEqual(m.year, 2016)
        self.assertEqual(m.month, 5)
        
        
    def test_init(self):
        m = _2016_5
        self.assertEqual(m.year, 2016)
        self.assertEqual(m.month, 5)
        
        
    def test_init_arg_type_errors(self):
        
        cases = [
            ('2016', '5'),
            ('2016', 5),
            (2016, '5')
        ]
        
        for case in cases:
            self._assert_raises(TypeError, CM, *case)
            
            
    def test_init_month_value_errors(self):
        
        cases = [
            (2016, -1),
            (2016, 0),
            (2016, 13)
        ]
        
        for case in cases:
            self._assert_raises(ValueError, CM, *case)
        
        
    def test_repr(self):
        self.assertEqual(repr(_2016_5), 'CalendarMonth(2016, 5)')
        
        
    def test_str(self):
        self.assertEqual(str(_2016_5), '2016-05')
        
        
    def test_as_dict_key(self):
        d = { _2016_5: 1 }
        self.assertEqual(d[_2016_5_], 1)
        
        
    def test_comparisons(self):
        
        a = _2016_5
        a_ = _2016_5_
        b = _2016_6
        
        self.assertFalse(a < a_)
        self.assertTrue(a < b)
        
        self.assertTrue(a <= a_)
        self.assertTrue(a <= b)
        
        self.assertTrue(a == a_)
        self.assertFalse(a == b)
        
        self.assertFalse(a != a_)
        self.assertTrue(a != b)
        
        self.assertFalse(a > a_)
        self.assertTrue(b > a)
        
        self.assertTrue(a >= a_)
        self.assertTrue(b >= a)
        
        
    def test_integer_arithmetic(self):
        
        cases = [
            (_2016_5, _2016_5, 0),
            (_2016_5, _2016_6, 1),
            (_2016_5, _2020_7, 50)
        ]
        
        for a, b, i in cases:
            
            self.assertEqual(a + i, b)
            self.assertEqual(i + a, b)
            self.assertEqual(b + -i, a)
            self.assertEqual(-i + b, a)
            
            self.assertEqual(a - -i, b)
            self.assertEqual(b - i, a)
        
            c = a
            c += i
            self.assertEqual(c, b)
            
            c = b
            c -= i
            self.assertEqual(c, a)
            
            self.assertEqual(b - a, i)
            
            
    def test_range(self):
        
        cases = [
            (_2016_6, _2016_5, []),
            (_2016_5, _2016_5, []),
            (_2016_5, _2016_6, [_2016_5]),
            (_2016_5, _2016_7, [_2016_5, _2016_6])
        ]
        
        for from_, to, expected in cases:
            result = list(CM.range(from_, to))
            self.assertEqual(result, expected)
        