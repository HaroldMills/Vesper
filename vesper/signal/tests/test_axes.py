from numbers import Number
import datetime

import numpy as np

from ..axis import Axis
from ..linear_mapping import LinearMapping
from ..time_axis import TimeAxis
from vesper.tests.test_case import TestCase


class AxisTests(TestCase):


    def test_axis_init(self):
         
        string_args_cases = [
            (),
            ('a',),
            ('a', 'b'),
            ('a', 'b', 'c')
        ]
         
        expected = (
            '', '', '', None, None, 0, None, None, None, LinearMapping())
         
        for args in string_args_cases:
            a = Axis(*args)
            expected = args + expected[len(args):]
            self._assert_axis(a, *expected)
                 
        m = LinearMapping(2, .5)
         
        complete_args_cases = [
            (('a', 'b', 'c', 0, 0, m), (None, None, 0, None, None, None, m)),
            (('p', 'q', 'r', 0, 10, m), (0, 9, 10, .5, 18.5, 18, m)),
            (('x', 'y', 'z', 5, 10, m), (5, 14, 10, 10.5, 28.5, 18, m)),
        ]
         
        for args, expected in complete_args_cases:
            a = Axis(*args)
            expected = args[:3] + expected
            self._assert_axis(a, *expected)
        
        
    def _assert_axis(
            self, a, name, units, units_abbreviation, start_index, end_index,
            length, start_value, end_value, span, mapping):
        
        self.assertEqual(a.name, name)
        self.assertEqual(a.units, units)
        self.assertEqual(a.units_abbreviation, units_abbreviation)
        self.assertEqual(a.start_index, start_index)
        self.assertEqual(a.end_index, end_index)
        self.assertEqual(a.length, length)
        self.assertEqual(a.start_value, start_value)
        self.assertEqual(a.end_value, end_value)
        self.assertEqual(a.span, span)
        self.assertEqual(a.index_to_value_mapping, mapping)


    def test_axis_index_to_value_mapping(self):
        
        a = Axis(index_to_value_mapping=LinearMapping(2, .5))
         
        cases = [
            (5, 10.5),
            (np.array([]), np.array([])),
            (np.array([0, 1]), np.array([.5, 2.5]))
        ]
         
        self._test_mapping(a, 'index_to_value', 'value_to_index', cases)
         
         
    def _test_mapping(self, a, forward_name, inverse_name, cases):
        
        for x, y in cases:
            
            method = getattr(a, forward_name)
            result = method(x)
            self._assert_equal(result, y)
             
            method = getattr(a, inverse_name)
            result = method(y)
            self._assert_equal(result, x)
            
            
    def _assert_equal(self, x, y):
        if isinstance(x, Number):
            self.assertEqual(x, y)
        else:
            self._assert_arrays_equal(x, y)
            

    def _assert_arrays_equal(self, x, y):
        self.assertTrue(np.alltrue(x == y))
        
        
    def test_time_axis_init(self):
        
        m = LinearMapping
        dt = datetime.datetime
        
        cases = [
                 
            ((5,), (None, None, 0,      # start index, end index, length
                    None, None, None,   # start time, end time, span
                    m(),                # index to value mapping
                    1, 1, 0,            # sample rate, sample period, duration
                    0, None,            # origin time, origin datetime
                    None, None)),       # start datetime, end datetime
                 
            ((5, 10), (5, 14, 10,
                       5, 14, 9,
                       m(),
                       1, 1, 10,
                       0, None,
                       None, None)),
            
            ((5, 10, 2), (5, 14, 10,
                          2.5, 7, 4.5,
                          m(.5),
                          2, .5, 5,
                          0, None,
                          None, None)),
                 
            ((5, 10, 2, .25), (5, 14, 10,
                               2.75, 7.25, 4.5,
                               m(.5, .25),
                               2, .5, 5,
                               .25, None,
                               None, None)),
                 
            ((5, 10, 2, .25, dt(2016, 4, 29, 1, 2, 3, 250000)),
                 (5, 14, 10,
                  2.75, 7.25, 4.5,
                  m(.5, .25),
                  2, .5, 5,
                  .25, dt(2016, 4, 29, 1, 2, 3, 250000),
                  dt(2016, 4, 29, 1, 2, 5, 750000),
                  dt(2016, 4, 29, 1, 2, 10, 250000)))
                 
        ]
         
        for args, expected in cases:
            a = TimeAxis(*args)
            self._assert_time_axis(a, *expected)
         
         
    def _assert_time_axis(self, a, *args):
        self._assert_axis(a, 'Time', 'seconds', 'S', *args[:7])
        (sample_rate, sample_period, duration, origin_time, origin_datetime,
            start_datetime, end_datetime) = args[7:]
        self.assertEqual(a.start_time, args[3])
        self.assertEqual(a.end_time, args[4])
        self.assertEqual(a.sample_rate, sample_rate)
        self.assertEqual(a.sample_period, sample_period)
        self.assertEqual(a.duration, duration)
        self.assertEqual(a.origin_time, origin_time)
        self.assertEqual(a.origin_datetime, origin_datetime)
        self.assertEqual(a.start_datetime, start_datetime)
        self.assertEqual(a.end_datetime, end_datetime)
        
        
    def test_time_axis_index_to_time_mapping(self):
        
        a = TimeAxis(5, 10, 2, .25)
         
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([10, 11]), np.array([5.25, 5.75]))
        ]
         
        self._test_mapping(a, 'index_to_time', 'time_to_index', cases)

    
    def test_time_axis_index_to_datetime_mapping(self):

        dt = datetime.datetime
        
        a = TimeAxis(5, 10, 2, .25, dt(2016, 4, 29, 1, 2, 3, 250000))
         
        cases = [
            (10, dt(2016, 4, 29, 1, 2, 8, 250000)),
            (np.array([]), []),
            (np.array([10, 11]),
                 np.array([dt(2016, 4, 29, 1, 2, 8, 250000),
                           dt(2016, 4, 29, 1, 2, 8, 750000)]))
        ]
         
        self._test_mapping(a, 'index_to_datetime', 'datetime_to_index', cases)
