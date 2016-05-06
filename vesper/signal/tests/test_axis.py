from vesper.signal.axis import Axis
from vesper.signal.tests.utils import DEFAULT_UNITS, TIME_UNITS
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class AxisTests(TestCase):


    @staticmethod
    def assert_axis(a, name, units):
        assert a.name == name
        assert a.units == units


    def test_init(self):
        args = ('Time', TIME_UNITS)
        defaults = (None, DEFAULT_UNITS)
        utils.test_init(args, defaults, Axis, self.assert_axis)
               
               
    def test_eq(self):
        args = ('Time', TIME_UNITS)
        changes = ('time', None)
        utils.test_eq(Axis, args, changes)
