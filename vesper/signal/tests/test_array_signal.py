from vesper.signal.array_signal import ArraySignal
from vesper.signal.tests.test_signal import SignalTests
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class ArraySignalTests(TestCase):


    @staticmethod
    def assert_signal(
            s, name, parent, time_axis, array_axes, amplitude_axis, samples):
        
        SignalTests.assert_signal(
            s, name, parent, time_axis, array_axes, amplitude_axis)
        
        assert s.dtype == samples.dtype
        utils.assert_arrays_equal(s[:], samples)

        
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
        
        samples = utils.create_samples((length, spectrum_size))
        
        args = (name, parent, time_axis, array_axes, power_axis, samples)
        
        s = ArraySignal(*args)
        
        self.assert_signal(s, *args)


    def test_shape_error(self):

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
        
        cases = [
            (length * spectrum_size,),
            (length + 1, spectrum_size),
            (length, spectrum_size + 1),
            (length, spectrum_size, 1)
        ]
        
        for shape in cases:
            samples = utils.create_samples(shape)
            args = (name, parent, time_axis, array_axes, power_axis, samples)
            self.assertRaises(ValueError, ArraySignal, *args)
        