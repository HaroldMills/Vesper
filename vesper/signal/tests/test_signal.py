from vesper.signal.signal import Signal
from vesper.signal.tests.test_signal_base import SignalBaseTests
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class SignalTests(TestCase):


    @staticmethod
    def assert_signal(s, name, parent, time_axis, array_axes, amplitude_axis):
        SignalBaseTests.assert_signal_base(
            s, name, time_axis, array_axes, amplitude_axis)
        assert s.parent == parent

        
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
        
        time_axis, array_axes, power_axis = utils.create_spectrogram_axes(
            start_index, length, sample_rate, spectrum_size, bin_size)
        
        args = (name, parent, time_axis, array_axes, power_axis)
        
        s = Signal(*args)
        
        self.assert_signal(s, *args)
        
        self.assertEqual(s.shape, (length, spectrum_size))
        self.assertEqual(len(s), length)
        
        self.assertRaises(NotImplementedError, getattr, s, 'dtype')
        self.assertRaises(NotImplementedError, s.__getitem__, 0)
