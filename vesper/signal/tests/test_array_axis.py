import numpy as np

from vesper.signal.array_axis import ArrayAxis
from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.tests.test_indexed_axis import IndexedAxisTests
from vesper.signal.tests.utils import DEFAULT_UNITS, FREQ_UNITS
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class ArrayAxisTests(TestCase):


    @staticmethod
    def assert_axis(a, name, units, length, mapping):
        
        IndexedAxisTests.assert_axis(a, name, units, 0, length)
        
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
        all_args = ('Frequency', FREQ_UNITS, 9, LinearMapping(10, .25))
        defaults = (None, DEFAULT_UNITS, 0, LinearMapping())
        utils.test_init(all_args, defaults, ArrayAxis, self.assert_axis)
        
        
    def test_eq(self):
        args = ('Frequency', FREQ_UNITS, 10, LinearMapping())
        changes = ('frequency', None, 0, LinearMapping(.5))
        utils.test_eq(ArrayAxis, args, changes)
        
        
    def test_index_to_value_mapping(self):
          
        a = ArrayAxis(index_to_value_mapping=LinearMapping(.5, .25))
           
        cases = [
            (10, 5.25),
            (np.array([]), np.array([])),
            (np.array([0, 1]), np.array([.25, .75]))
        ]
           
        utils.test_mapping(a, 'index_to_value', 'value_to_index', cases)
