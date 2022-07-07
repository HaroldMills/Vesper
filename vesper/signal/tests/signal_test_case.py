import numpy as np

from vesper.tests.test_case import TestCase
import vesper.signal.tests.utils as utils


NUM_INDEXING_TESTS = 100


class SignalTestCase(TestCase):


    def assert_signal(
            self, s, name, time_axis, channel_count, item_shape, dtype,
            samples=None):
        
        # If provided, `samples` must be channel-first.
        
        self._assert_metadata(s, name, time_axis, item_shape, dtype)
        
        self._check_signal_indexer(s.as_frames, s, True)
        self._check_signal_indexer(s.as_channels, s, False)
        
        if samples is not None:
            utils.test_indexing(s.as_channels, samples, NUM_INDEXING_TESTS)
            utils.test_indexing(
                s.as_frames, samples.swapaxes(0, 1), NUM_INDEXING_TESTS)
        
        self.assertEqual(len(s.channels), channel_count)
        self.assertEqual(s.channel_count, channel_count)
        
        for i in range(channel_count):
            
            name = str(i)
            
            if samples is None:
                channel_samples = None
            else:
                channel_samples = samples[i]
 
            # Check channel access by index.
            c = s.channels[i]
            self.assert_channel(
                c, s, name, i, time_axis, item_shape, dtype, channel_samples)
            
            # Check channel access by name.
            c = s.channels[name]
            self.assert_channel(
                c, s, name, i, time_axis, item_shape, dtype, channel_samples)
             
            
    def _assert_metadata(self, s, name, time_axis, item_shape, dtype):
        self.assertEqual(s.name, name)
        self.assertEqual(s.time_axis, time_axis)
        self.assertEqual(len(s), time_axis.length)
        self.assertEqual(s.frame_rate, time_axis.frame_rate)
        self.assertEqual(s.frame_period, time_axis.frame_period)
        self.assertEqual(s.sample_rate, time_axis.sample_rate)
        self.assertEqual(s.sample_period, time_axis.sample_period)
        self.assertEqual(s.item_shape, item_shape)
        self.assertEqual(s.dtype, np.dtype(dtype))


    def _check_signal_indexer(self, r, s, frame_first):
        
        self.assertIs(r.signal, s)
        self.assertEqual(r.frame_first, frame_first)
        
        frame_count = s.time_axis.length
        channel_count = len(s.channels)
        
        if frame_first:
            self.assertEqual(len(r), frame_count)
            self.assertEqual(
                r.shape, (frame_count, channel_count) + s.item_shape)
        else:
            self.assertEqual(len(r), channel_count)
            self.assertEqual(
                r.shape, (channel_count, frame_count) + s.item_shape)
            
        self.assertEqual(r.dtype, s.dtype)
    

    def assert_channel(
            self, c, signal, name, index, time_axis, item_shape, dtype,
            samples=None):
        
        # If provided, `samples` must be channel-first.
        
        self._assert_metadata(c, name, time_axis, item_shape, dtype)
        
        self.assertEqual(c.signal, signal)
        self.assertEqual(c.index, index)
             
        if samples is not None:
            utils.test_indexing(c, samples, NUM_INDEXING_TESTS)
