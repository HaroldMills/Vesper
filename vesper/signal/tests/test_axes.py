from numbers import Number
import datetime

import numpy as np

from ..amplitude_axis import AmplitudeAxis
from ..axis import Axis
from ..index_axis import IndexAxis
from ..linear_mapping import LinearMapping
from ..sample_array_axis import SampleArrayAxis
from ..time_axis import TimeAxis
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch


_DEFAULT_UNITS = Bunch(plural=None, singular=None, abbreviation=None)
_TIME_UNITS = Bunch(plural='seconds', singular='second', abbreviation='S')
_FREQ_UNITS = Bunch(plural='hertz', singular='hertz', abbreviation='Hz')
_POWER_UNITS = Bunch(plural='decibels', singular='decibel', abbreviation='dB')


class AxisTests(TestCase):


    def test_axis_init(self):
        all_args = ('Time', _TIME_UNITS)
        defaults = (None, _DEFAULT_UNITS)
        self._test_axis_init(all_args, defaults, Axis, self._assert_axis)
               
               
    def _test_axis_init(self, all_args, defaults, cls, assert_method): 
        for i in range(len(all_args)):
            args = all_args[:i]
            a = cls(*args)
            expected = all_args[:i] + defaults[i:]
            assert_method(a, *expected)
                        
            
    def _assert_axis(self, a, name, units):
        self.assertEqual(a.name, name)
        self.assertEqual(a.units, units)


    def test_index_axis_init(self):
        
        name = 'Time'
        units = Bunch(plural='seconds', singular='second', abbreviation='S')
        start_index = 5
        length = 10    
        all_args = (name, units, start_index, length)
        
        defaults = (None, _DEFAULT_UNITS, 0, 0)
        
        self._test_axis_init(
            all_args, defaults, IndexAxis, self._assert_index_axis)
            
            
    def _assert_index_axis(self, a, name, units, start_index, length):
        self._assert_axis(a, name, units)
        self.assertEqual(a.start_index, start_index)
        self.assertEqual(a.length, length)
        end_index = start_index + length - 1 if length != 0 else None
        self.assertEqual(a.end_index, end_index)
        
        
    def test_time_axis_init(self):
                 
        start_index = 5
        length = 10
        sample_rate = 2
        mapping = LinearMapping(1 / sample_rate, .25)
        start_datetime = datetime.datetime(2016, 5, 4, 1, 2, 3, 250000)
        reference = Bunch(index=start_index, datetime=start_datetime)
        all_args = (start_index, length, sample_rate, mapping, reference)
         
        defaults = (0, 0, 1, None, None)
         
        for i in range(len(all_args)):
             
            args = all_args[:i]
             
            a = TimeAxis(*args)
             
            expected = all_args[:i] + defaults[i:]
             
            if expected[-1] is None:
                start_datetime = None
                end_datetime = None
            else:
                seconds = (length - 1) / sample_rate
                td = datetime.timedelta(seconds=seconds)
                end_datetime = start_datetime + td
                 
            expected = expected + (start_datetime, end_datetime)
             
            self._assert_time_axis(a, *expected)
        
        
    def _assert_time_axis(
            self, a, start_index, length, sample_rate, mapping, reference,
            start_datetime, end_datetime):
        
        sample_period = 1 / sample_rate
        
        self._assert_index_axis(a, 'Time', _TIME_UNITS, start_index, length)
        
        self.assertEqual(a.sample_rate, sample_rate)
        self.assertEqual(a.sample_period, sample_period)
        
        if mapping is None:
            mapping = LinearMapping(sample_period)
        self.assertEqual(a.index_to_time_mapping, mapping)
        
        start_time = mapping.map(a.start_index)
        self.assertEqual(a.start_time, start_time)
        
        end_time = mapping.map(a.end_index) if length != 0 else None
        self.assertEqual(a.end_time, end_time)
        
        span = end_time - start_time if length != 0 else None
        self.assertEqual(a.span, span)
        
        duration = span + sample_period if length != 0 else 0
        self.assertEqual(a.duration, duration)
        
        self.assertEqual(a.reference_datetime, reference)
        self.assertEqual(a.start_datetime, start_datetime)
        self.assertEqual(a.end_datetime, end_datetime)
            

    def test_time_axis_index_to_time_mapping(self):
          
        a = TimeAxis(5, 10, 2, LinearMapping(.5, .25))
           
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([10, 11]), np.array([5.25, 5.75]))
        ]
           
        self._test_mapping(a, 'index_to_time', 'time_to_index', cases)
  
      
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
         
         
    def test_time_axis_index_to_datetime_mapping(self):
  
        dt = datetime.datetime
          
        reference = Bunch(index=5, datetime=dt(2016, 4, 29, 1, 2, 3))
        a = TimeAxis(5, 10, 2, None, reference)
           
        cases = [
            (10, dt(2016, 4, 29, 1, 2, 5, 500000)),
            (np.array([]), []),
            (np.array([9, 11]),
                 np.array([dt(2016, 4, 29, 1, 2, 5), dt(2016, 4, 29, 1, 2, 6)]))
        ]
           
        self._test_mapping(a, 'index_to_datetime', 'datetime_to_index', cases)
        
        
    def test_sample_array_axis_init(self):
        
        name = 'Frequency'
        units = _FREQ_UNITS
        length = 9
        mapping = LinearMapping(10, .25)
        all_args = (name, units, length, mapping)
        
        defaults = (None, _DEFAULT_UNITS, 0, LinearMapping())
        
        self._test_axis_init(
            all_args, defaults, SampleArrayAxis, self._assert_sample_array_axis)
        
        
    def _assert_sample_array_axis(self, a, name, units, length, mapping):
        
        self._assert_index_axis(a, name, units, 0, length)
        
        if mapping is None:
            mapping = LinearMapping()
        self.assertEqual(a.index_to_value_mapping, mapping)
        
        start_value = mapping.map(a.start_index)
        self.assertEqual(a.start_value, start_value)
        
        end_value = mapping.map(a.end_index) if length != 0 else None
        self.assertEqual(a.end_value, end_value)
        
        span = end_value - start_value if length != 0 else None
        self.assertEqual(a.span, span)
                    
        
    def test_sample_array_axis_index_to_value_mapping(self):
          
        a = SampleArrayAxis(index_to_value_mapping=LinearMapping(.5, .25))
           
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([0, 1]), np.array([.25, .75]))
        ]
           
        self._test_mapping(a, 'index_to_value', 'value_to_index', cases)

    
    def test_amplitude_axis(self):
        all_args = ('Power', _POWER_UNITS)
        defaults = ('Amplitude', _DEFAULT_UNITS)
        self._test_axis_init(
            all_args, defaults, AmplitudeAxis, self._assert_axis)
