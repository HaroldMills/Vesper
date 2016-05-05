import numpy as np

from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.sample_array_axis import SampleArrayAxis
from vesper.signal.tests.axis_test_case import AxisTestCase
from vesper.signal.tests.axis_units import DEFAULT_UNITS, FREQ_UNITS
from vesper.signal.tests.test_index_axis import IndexAxisTests


class SampleArrayAxisTests(AxisTestCase):


    @staticmethod
    def assert_axis(a, name, units, length, mapping):
        
        IndexAxisTests.assert_axis(a, name, units, 0, length)
        
        if mapping is None:
            mapping = LinearMapping()
        assert a.index_to_value_mapping == mapping
        
        start_value = mapping.map(a.start_index)
        assert a.start_value == start_value
        
        end_value = mapping.map(a.end_index) if length != 0 else None
        assert a.end_value == end_value
        
        span = end_value - start_value if length != 0 else None
        assert a.span == span
                    
        
    def test_init(self):
        
        name = 'Frequency'
        units = FREQ_UNITS
        length = 9
        mapping = LinearMapping(10, .25)
        all_args = (name, units, length, mapping)
        
        defaults = (None, DEFAULT_UNITS, 0, LinearMapping())
        
        self._test_init(
            all_args, defaults, SampleArrayAxis, self.assert_axis)
        
        
    def test_eq(self):
        args = ('Frequency', FREQ_UNITS, 10, LinearMapping())
        changes = ('frequency', None, 0, LinearMapping(.5))
        self._test_eq(SampleArrayAxis, args, changes)
        
        
    def test_index_to_value_mapping(self):
          
        a = SampleArrayAxis(index_to_value_mapping=LinearMapping(.5, .25))
           
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([0, 1]), np.array([.25, .75]))
        ]
           
        self._test_mapping(a, 'index_to_value', 'value_to_index', cases)
