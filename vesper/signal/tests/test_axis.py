from vesper.signal.axis import Axis
from vesper.signal.tests.axis_test_case import AxisTestCase
import vesper.signal.tests.axis_units as units


class AxisTests(AxisTestCase):


    @staticmethod
    def assert_axis(a, name, units):
        assert a.name == name
        assert a.units == units


    def test_init(self):
        args = ('Time', units.TIME_UNITS)
        defaults = (None, units.DEFAULT_UNITS)
        self._test_init(args, defaults, Axis, self.assert_axis)
               
               
    def test_eq(self):
        args = ('Time', units.TIME_UNITS)
        changes = ('time', None)
        self._test_eq(Axis, args, changes)
