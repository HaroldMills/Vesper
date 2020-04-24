import numpy as np

from vesper.signal.signal import Signal
from vesper.signal.time_axis import TimeAxis
from vesper.tests.test_case import TestCase


class SignalTests(TestCase):


    @staticmethod
    def assert_signal(s, name, time_axis, channel_count, array_shape, dtype):
        
        _assert_metadata(s, name, time_axis, array_shape, dtype)
        
        assert len(s.channels) == channel_count
        
        for i in range(channel_count):
            
            name = str(i)
            
            # Check channel access by number.
            c = s.channels[i]
            SignalTests.assert_channel(
                c, s, name, i, time_axis, array_shape, dtype)
            
            # Check channel access by name.
            c = s.channels[name]
            SignalTests.assert_channel(
                c, s, name, i, time_axis, array_shape, dtype)
             
            
    @staticmethod
    def assert_channel(c, signal, name, number, time_axis, array_shape, dtype):
        
        _assert_metadata(c, name, time_axis, array_shape, dtype)
        
        assert c.signal == signal
        assert c.number == number
             
        
    def test_init(self):
        
        cases = [
            ('A', 0, 0, (), 'int16'),
            ('B', 2, 0, (10,), 'float'),
            ('Bobo', 0, 3, (20, 30), '<i2'),
            ('Bibi', 1, 2, (40, 50, 60), '>i4'),
        ]
        
        frame_rate = 24000
        
        for name, length, channel_count, array_shape, dtype in cases:
            
            time_axis = TimeAxis(length, frame_rate)
            s = Signal(time_axis, channel_count, array_shape, dtype, name)
            
            self.assert_signal(
                s, name, time_axis, channel_count, array_shape, dtype)
        
            # Check initializer with default name.
            s = Signal(time_axis, channel_count, array_shape, dtype)
            self.assert_signal(
                s, 'Signal', time_axis, channel_count, array_shape, dtype)
                        
            
def _assert_metadata(s, name, time_axis, array_shape, dtype):
    assert s.name == name
    assert s.time_axis == time_axis
    assert s.array_shape == array_shape
    assert s.dtype == np.dtype(dtype)
