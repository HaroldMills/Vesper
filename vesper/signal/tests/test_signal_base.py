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
            
            time_axis, array_axes, amplitude_axis = \
                utils.create_signal_axes(shape)
                
            args = ('Signal', time_axis, array_axes, amplitude_axis)
            
            s = SignalBase(*args)
            
            self.assert_signal_base(s, *args)
            
            self.assertRaises(NotImplementedError, getattr, s, 'dtype')
            self.assertRaises(NotImplementedError, getattr, s, 'shape')
            self.assertRaises(NotImplementedError, len, s)
            self.assertRaises(NotImplementedError, s.__getitem__, 0)
