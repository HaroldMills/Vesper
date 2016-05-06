from vesper.signal.multichannel_signal import MultichannelSignal
from vesper.signal.signal import Signal
from vesper.signal.tests.test_signal_base import SignalBaseTests
from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


class MultichannelSignalTests(TestCase):


    @staticmethod
    def assert_multichannel_signal(
            s, name, channel_names, time_axis, array_axes, amplitude_axis):
        
        SignalBaseTests.assert_signal_base(
            s, name, time_axis, array_axes, amplitude_axis)
        
        names = tuple(c.name for c in s.channels)
        assert names == channel_names

        num_channels = len(channel_names)
        time_axis_length = time_axis.length
        sample_array_shape = tuple(a.length for a in array_axes)
        shape = (num_channels, time_axis_length) + sample_array_shape
        assert s.shape == shape
        assert len(s) == num_channels
        
        
    def test_init(self):
        
        shapes = [
            (0, 0),
            (1, 0),
            (1, 2),
            (1, 2, 3),
            (2, 3),
            (2, 3, 4),
            (4, 2, 3)
        ]
        
        for shape in shapes:
            
            channel_names = \
                tuple('Channel ' + str(i) for i in range(shape[0]))
            
            time_axis, array_axes, amplitude_axis = \
                utils.create_signal_axes(shape[1:])
            
            args = ('Signal', channel_names, time_axis, array_axes,
                    amplitude_axis)
            
            s = _MultichannelSignal(*args)
            
            self.assert_multichannel_signal(s, *args)
            
            self.assertRaises(NotImplementedError, getattr, s, 'dtype')
            self.assertRaises(NotImplementedError, s.__getitem__, 0)


class _MultichannelSignal(MultichannelSignal):
    
    
    def __init__(
            self, name, channel_names, time_axis, array_axes, amplitude_axis):
        
        channels = tuple(
            Signal(name, self, time_axis, array_axes, amplitude_axis)
            for name in channel_names)
        
        super().__init__(name, channels, time_axis, array_axes, amplitude_axis)
