from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.tests.axis_test_case import AxisTestCase
from vesper.signal.tests.test_axis import AxisTests
from vesper.signal.tests.utils import DEFAULT_UNITS, POWER_UNITS


class AmplitudeAxisTests(AxisTestCase):


    def test_init(self):
        args = ('Power', POWER_UNITS)
        defaults = ('Amplitude', DEFAULT_UNITS)
        self._test_init(args, defaults, AmplitudeAxis, AxisTests.assert_axis)


    def test_eq(self):
        args = ('Power', POWER_UNITS)
        changes = ('power', None)
        self._test_eq(AmplitudeAxis, args, changes)
