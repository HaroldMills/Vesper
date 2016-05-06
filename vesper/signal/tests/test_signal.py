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

        time_axis_length = time_axis.length
        array_shape = tuple(a.length for a in array_axes)
        shape = (time_axis_length,) + array_shape
        assert s.shape == shape
        assert len(s) == time_axis_length

        
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
        
            # In practice the parent of a `Signal` will be either a
            # `MultichannelSignal` or `None`. We use a string here for
            # simplicity.
            args = ('Signal', 'Parent', time_axis, array_axes, amplitude_axis)
            
            s = Signal(*args)
            
            self.assert_signal(s, *args)
            
            self.assertEqual(s.shape, shape)
            self.assertEqual(len(s), shape[0])
            
            self.assertRaises(NotImplementedError, getattr, s, 'dtype')
            self.assertRaises(NotImplementedError, s.__getitem__, 0)
