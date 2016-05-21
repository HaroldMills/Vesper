from vesper.signal.array_signal import ArraySignal
from vesper.signal.tests.test_signal import SignalTests
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class ArraySignalTests(TestCase):


    @staticmethod
    def assert_array_signal(
            s, name, parent, time_axis, array_axes, amplitude_axis, samples):
        
        SignalTests.assert_signal(
            s, name, parent, time_axis, array_axes, amplitude_axis)
        
        assert s.dtype == samples.dtype
        utils.assert_arrays_equal(s[:], samples, strict=True)

        
    def test_init(self):
        
        shapes = [
            (0,),
            (1,),
            (2,),
            (2, 0),
            (2, 1),
            (2, 3),
            (2, 3, 4)
        ]
        
        for shape in shapes:
            
            samples = utils.create_samples(shape)
            
            time_axis, array_axes, amplitude_axis = \
                utils.create_signal_axes(shape)
                
            # In practice the parent of a `ArraySignal` will be either a
            # `MultichannelSignal` or `None`. We use a string here for
            # simplicity.
            args = (samples, 'Signal', 'Parent', time_axis, array_axes,
                    amplitude_axis)
            
            s = ArraySignal(*args)
            
            self.assert_array_signal(s, *(args[1:] + args[:1]))


    def test_init_shape_error(self):

        m = 2
        n = 3
        shape = (m, n)
        time_axis, array_axes, power_axis = utils.create_signal_axes(shape)
        
        shapes = [
            (m * n,),
            (m + 1, n),
            (m, n + 1),
            (m, n, 1)
        ]
        
        for shape in shapes:
            
            samples = utils.create_samples(shape)
            
            # In practice the parent of an `ArraySignal` will be either a
            # `MultichannelSignal` or `None`. We use a string here for
            # simplicity.
            args = (samples, 'Signal', 'Parent', time_axis, array_axes,
                    power_axis)
            
            self._assert_raises(ValueError, ArraySignal, *args)
        