from vesper.signal.indexed_axis import IndexedAxis
from vesper.signal.tests.test_axis import AxisTests
from vesper.signal.tests.utils import DEFAULT_UNITS, TIME_UNITS
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class IndexedAxisTests(TestCase):


    @staticmethod
    def assert_axis(a, name, units, start_index, length):
        AxisTests.assert_axis(a, name, units)
        assert a.start_index == start_index
        assert a.length == length
        end_index = start_index + length - 1 if length != 0 else None
        assert a.end_index == end_index
        
        
    def test_init(self):
        args = ('Time', TIME_UNITS, 5, 10)
        defaults = (None, DEFAULT_UNITS, 0, 0)
        utils.test_init(args, defaults, IndexedAxis, self.assert_axis)
            
            
    def test_eq(self):
        args = ('Time', TIME_UNITS, 5, 10)
        changes = ('time', None, 0, 0)
        utils.test_eq(IndexedAxis, args, changes)
