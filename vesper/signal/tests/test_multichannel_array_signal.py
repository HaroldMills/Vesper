from vesper.signal.multichannel_array_signal import MultichannelArraySignal
from vesper.signal.tests.test_multichannel_signal import MultichannelSignalTests
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class MultichannelArraySignalTests(TestCase):


    @staticmethod
    def assert_multichannel_array_signal(
            s, name, channel_names, time_axis, array_axes, amplitude_axis,
            samples):
        
        MultichannelSignalTests.assert_multichannel_signal(
            s, name, channel_names, time_axis, array_axes, amplitude_axis)

        utils.assert_arrays_equal(s[:], samples, strict=True)
        
        
    def test_init(self):
        
        shapes = [
#            (0, 0),
#            (1, 0),
            (1, 2),
            (1, 2, 3),
            (2, 3),
            (2, 3, 4),
            (4, 2, 3)
        ]
        
        for shape in shapes:
            
            samples = utils.create_samples(shape)

            channel_names = tuple(str(i) for i in range(shape[0]))
            
            time_axis, array_axes, amplitude_axis = \
                utils.create_signal_axes(shape[1:])
            
            args = (samples, 'Signal', channel_names, time_axis, array_axes,
                    amplitude_axis)
            
            s = MultichannelArraySignal(*args)
            
            self.assert_multichannel_array_signal(s, *(args[1:] + args[:1]))

    
    def test_init_shape_error(self):

        m = 2
        n = 3
        shape = (m, n)
        time_axis, array_axes, power_axis = utils.create_signal_axes(shape)
        
        shapes = [
            (2, m * n,),
            (2, m + 1, n),
            (2, m, n + 1),
            (2, m, n, 1)
        ]
        
        channel_names = ('Left', 'Right')
        
        for shape in shapes:
            
            samples = utils.create_samples(shape)
            
            args = (samples, 'Signal', channel_names, time_axis, array_axes,
                    power_axis)
            
            self._assert_raises(ValueError, MultichannelArraySignal, *args)
        