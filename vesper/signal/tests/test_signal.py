import datetime

from vesper.signal.amplitude_axis import AmplitudeAxis
from vesper.signal.array_axis import ArrayAxis
from vesper.signal.linear_mapping import LinearMapping
from vesper.signal.named_sequence import NamedSequence
from vesper.signal.signal import Signal
from vesper.signal.tests.axis_units import FREQ_UNITS, POWER_UNITS
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch


class SignalTests(TestCase):


    @staticmethod
    def assert_signal(
            s, name, parent, time_axis, array_axes, amplitude_axis):
        
        assert s.name == name
        assert s.parent == parent
        assert s.time_axis == time_axis
        assert s.array_axes == NamedSequence(array_axes)
        assert s.amplitude_axis == amplitude_axis

        
    def test_init(self):
        
        start_index = 5
        length = 10
        sample_rate = 2
        spectrum_size = 9
        bin_size = 20
        
        name = 'Signal'
        
        # In practice the parent of a `Signal` will be either a
        # `MultichannelSignal` or `None`. We use a string here for simplicity.
        parent = 'Parent'
        
        reference = Bunch(index=start_index, datetime=datetime.datetime.now())
        time_axis = TimeAxis(
            start_index, length, sample_rate, reference_datetime=reference)
        
        frequency_axis = ArrayAxis(
            name='Frequency', units=FREQ_UNITS, length=spectrum_size,
            index_to_value_mapping=LinearMapping(bin_size))
        array_axes = [frequency_axis]
        
        power_axis = AmplitudeAxis(name='Power', units=POWER_UNITS)
        
        args = (name, parent, time_axis, array_axes, power_axis)
        
        s = Signal(*args)
        
        self.assert_signal(s, *args)
        
        self.assertEqual(s.axes['Time'], time_axis)
        self.assertEqual(s.axes['Frequency'], frequency_axis)
        self.assertEqual(s.axes['Power'], power_axis)
        self.assertRaises(NotImplementedError, getattr, s, 'dtype')
        self.assertEqual(s.shape, (length, spectrum_size))
        self.assertEqual(len(s), length)
        self.assertRaises(NotImplementedError, s.__getitem__, 0)
