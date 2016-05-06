from vesper.signal.named_sequence import NamedSequence
from vesper.signal.signal_base import SignalBase
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class SignalBaseTests(TestCase):


    @staticmethod
    def assert_signal_base(s, name, time_axis, array_axes, amplitude_axis):
        
        assert s.name == name
        assert s.time_axis == time_axis
        assert s.array_axes == NamedSequence(array_axes)
        assert s.amplitude_axis == amplitude_axis
        
        axes = (time_axis,) + tuple(array_axes) + (amplitude_axis,)
        for axis in axes:
            assert s.axes[axis.name] == axis

        
    def test_init(self):
        
        start_index = 5
        length = 10
        sample_rate = 2
        spectrum_size = 9
        bin_size = 20
        
        name = 'Signal'
        
        time_axis, array_axes, power_axis = utils.create_spectrogram_axes(
            start_index, length, sample_rate, spectrum_size, bin_size)
            
        args = (name, time_axis, array_axes, power_axis)
        
        s = SignalBase(*args)
        
        self.assert_signal_base(s, *args)
        
        self.assertRaises(NotImplementedError, getattr, s, 'dtype')
        self.assertRaises(NotImplementedError, getattr, s, 'shape')
        self.assertRaises(NotImplementedError, len, s)
        self.assertRaises(NotImplementedError, s.__getitem__, 0)
