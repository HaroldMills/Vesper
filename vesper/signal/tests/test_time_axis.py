import datetime

import numpy as np

from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.tests.axis_test_case import AxisTestCase
from vesper.signal.tests.axis_units import TIME_UNITS
from vesper.signal.tests.test_indexed_axis import IndexedAxisTests
from vesper.signal.time_axis import TimeAxis
from vesper.util.bunch import Bunch


class TimeAxisTests(AxisTestCase):


    @staticmethod
    def assert_axis(
            a, start_index, length, sample_rate, mapping, reference,
            start_datetime, end_datetime):
        
        sample_period = 1 / sample_rate
        
        IndexedAxisTests.assert_axis(a, 'Time', TIME_UNITS, start_index, length)
        
        assert a.sample_rate == sample_rate
        assert a.sample_period == sample_period
        
        if mapping is None:
            mapping = LinearMapping(sample_period)
        assert a.index_to_time_mapping == mapping
        
        start_time = mapping.map(a.start_index)
        assert a.start_time == start_time
        
        end_time = mapping.map(a.end_index) if length != 0 else None
        assert a.end_time == end_time
        
        span = end_time - start_time if length != 0 else None
        assert a.span == span
        
        duration = span + sample_period if length != 0 else 0
        assert a.duration == duration
        
        assert a.reference_datetime == reference
        assert a.start_datetime == start_datetime
        assert a.end_datetime == end_datetime
            

    def test_init(self):
                 
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
             
            self.assert_axis(a, *expected)
            
            
    def test_eq(self):
        args = (5, 10, 2, LinearMapping(.5), None)
        reference_datetime = Bunch(index=0, datetime=datetime.datetime.now())
        changes = (0, 0, 1, LinearMapping(1), reference_datetime)
        self._test_eq(TimeAxis, args, changes)
        
        
    def test_index_to_time_mapping(self):
          
        a = TimeAxis(5, 10, 2, LinearMapping(.5, .25))
           
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([10, 11]), np.array([5.25, 5.75]))
        ]
           
        self._test_mapping(a, 'index_to_time', 'time_to_index', cases)
  
      
    def test_index_to_datetime_mapping(self):
  
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
