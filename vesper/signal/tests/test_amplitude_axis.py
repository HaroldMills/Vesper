from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.tests.test_axis import AxisTests
from vesper.signal.tests.utils import DEFAULT_UNITS, POWER_UNITS
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class AmplitudeAxisTests(TestCase):


    def test_init(self):
        args = ('Power', POWER_UNITS)
        defaults = ('Amplitude', DEFAULT_UNITS)
        utils.test_init(args, defaults, AmplitudeAxis, AxisTests.assert_axis)


    def test_eq(self):
        args = ('Power', POWER_UNITS)
        changes = ('power', None)
        utils.test_eq(AmplitudeAxis, args, changes)
