from vesper.signal.indexed_axis import IndexedAxis
from vesper.signal.tests.axis_test_case import AxisTestCase
from vesper.signal.tests.test_axis import AxisTests
from vesper.signal.tests.utils import DEFAULT_UNITS, TIME_UNITS
from vesper.util.bunch import Bunch


class IndexedAxisTests(AxisTestCase):


    @staticmethod
    def assert_axis(a, name, units, start_index, length):
        AxisTests.assert_axis(a, name, units)
        assert a.start_index == start_index
        assert a.length == length
        end_index = start_index + length - 1 if length != 0 else None
        assert a.end_index == end_index
        
        
    def test_init(self):
        
        name = 'Time'
        units = Bunch(plural='seconds', singular='second', abbreviation='S')
        start_index = 5
        length = 10    
        args = (name, units, start_index, length)
        
        defaults = (None, DEFAULT_UNITS, 0, 0)
        
        self._test_init(args, defaults, IndexedAxis, self.assert_axis)
            
            
    def test_eq(self):
        args = ('Time', TIME_UNITS, 5, 10)
        changes = ('time', None, 0, 0)
        self._test_eq(IndexedAxis, args, changes)
