from vesper.recorder.audio_input_chunk import Int16AudioInputChunk
import itertools

import numpy as np

from vesper.tests.test_case import TestCase


chain = itertools.chain.from_iterable


CHUNK_TYPES = (Int16AudioInputChunk,)
CHANNEL_COUNTS = tuple(range(1, 5))



class AudioInputChunkTests(TestCase):


    def test_init(self):
         _test(self._test_init)


    def _test_init(self, chunk_type, channel_count):
         c = chunk_type(channel_count, 4)
         self.assertEqual(c.channel_count, channel_count)
         self.assertEqual(c.capacity, 4)
         self.assert_chunk_empty(c)


    def assert_chunk_empty(self, c):
        self.assertEqual(c.size, 0)
        expected = np.zeros((c.channel_count, 0), dtype='float32')
        self.assert_arrays_equal(c.samples, expected)


    def test_write_read(self):
        _test(self._test_write_read)


    def _test_write_read(self, chunk_type, channel_count):

        c = chunk_type(channel_count, 5)

        frame_count = write(c, -2, 0)
        self.assertEqual(frame_count, 3)
        self.assert_chunk(c, -2, 0)

        frame_count = write(c, 1, 2)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, -2, 2)


    def assert_chunk(self, c, start_value, end_value):

        samples = get_samples(c.channel_count, start_value, end_value)

        format = c.input_sample_format
        expected_samples = format.normalize_samples(samples)

        expected_size = expected_samples.shape[1]
        self.assertEqual(c.size, expected_size)

        self.assert_arrays_equal(c.samples, expected_samples)


    def test_write_with_start_frame_num(self):
        _test(self._test_write_with_start_frame_num)


    def _test_write_with_start_frame_num(self, chunk_type, channel_count):

        c = chunk_type(channel_count, 4)

        frame_count = write(c, 1, 4, start_frame_num=2)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 3, 4)

        frame_count = write(c, 5, 6)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 3, 6)


    def test_write_with_frame_count(self):
        _test(self._test_write_with_frame_count)


    def _test_write_with_frame_count(self, chunk_type, channel_count):
       
        c = chunk_type(channel_count, 4)

        frame_count = write(c, 1, 4, frame_count=2)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 1, 2)

        frame_count = write(c, 3, 4)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 1, 4)


    def test_write_with_optional_args(self):
        _test(self._test_write_with_optional_args)


    def _test_write_with_optional_args(self, chunk_type, channel_count):

        c = chunk_type(channel_count, 4)

        frame_count = write(c, 1, 6, start_frame_num=1, frame_count=2)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 2, 3)

        frame_count = write(c, 4, 5)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 2, 5)


    def test_partial_write(self):
        _test(self._test_partial_write)


    def _test_partial_write(self, chunk_type, channel_count):

        c = chunk_type(channel_count, 4)

        frame_count = write(c, 1, 2)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 1, 2)

        # Here we expect that not all frames will be written, since
        # we're trying to write more frames than are left in the chunk.
        frame_count = write(c, 3, 6)
        self.assertEqual(frame_count, 2)
        self.assert_chunk(c, 1, 4)


    def test_clear(self):
        _test(self._test_clear)


    def _test_clear(self, chunk_type, channel_count):

        c = chunk_type(channel_count, 4)

        frame_count = write(c, 1, 3)
        self.assertEqual(frame_count, 3)
        self.assert_chunk(c, 1, 3)

        c.clear()
        self.assert_chunk_empty(c)

        frame_count = write(c, 5, 8)
        self.assertEqual(frame_count, 4)
        self.assert_chunk(c, 5, 8)


def _test(method):
    for chunk_type in CHUNK_TYPES:
        for channel_count in CHANNEL_COUNTS:
            method(chunk_type, channel_count)


def write(chunk, start_value, end_value, start_frame_num=0, frame_count=None):
    data = get_raw_sample_data(chunk, start_value, end_value)
    return chunk.write(data, start_frame_num, frame_count)


def get_raw_sample_data(chunk, start_value, end_value):
    samples = get_samples(chunk.channel_count, start_value, end_value)
    format = chunk.input_sample_format
    return format.get_raw_sample_data(samples)


def get_samples(channel_count, start_value, end_value):

    # Get channel offsets in an array of shape (channel_count, 1).
    offsets = 100 * np.arange(channel_count).reshape(channel_count, 1)

    # Get channel zero sample values in an array of shape (1, value_count).
    value_count = end_value - start_value + 1
    values = np.arange(start_value, end_value + 1).reshape(1, value_count)

    # Get samples for all channels, taking advantage of NumPy broadcasting.
    samples = offsets + values

    return samples
