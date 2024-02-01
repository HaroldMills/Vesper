import numpy as np

from vesper.recorder.audio_input_buffer import (
    AudioInputBuffer, AudioInputBufferOverflow)
from vesper.recorder.audio_input_chunk import Int16AudioInputChunk
from vesper.tests.test_case import TestCase


CHANNEL_COUNTS = tuple(range(1, 5))

CHUNK_TYPES = (Int16AudioInputChunk,)


class AudioInputBufferTests(TestCase):


    def test_init(self):
         _test(self._test_init)


    def _test_init(self, channel_count, chunk_type):
         b = create_buffer(channel_count, 4, 5, chunk_type)
         self.assertEqual(b.channel_count, channel_count)
         self.assertEqual(b.capacity, 4)
         self.assertEqual(b.chunk_size, 5)
         self.assert_empty(b)


    def test_write_read(self):
        _test(self._test_write_read)


    def _test_write_read(self, channel_count, chunk_type):

        b = create_buffer(channel_count, 3, 10, chunk_type)
        self.assert_empty(b)

        write(b, 1, 4)
        self.assert_empty(b)

        write(b, 5, 8)
        self.assert_empty(b)

        write(b, 9, 12)
        self.assert_size(b, 1)

        chunk = self.assert_chunk(b, 1, 10)
        self.assert_empty(b)

        b.free_chunk(chunk)
        self.assert_empty(b)

        write(b, 13, 20)
        self.assert_size(b, 1)

        write(b, 21, 30)
        self.assert_size(b, 2)

        chunk_a = self.assert_chunk(b, 11, 20)
        self.assert_size(b, 1)

        chunk_b = self.assert_chunk(b, 21, 30)
        self.assert_empty(b)

        b.free_chunk(chunk_a)
        b.free_chunk(chunk_b)
        self.assert_empty(b)


    def test_wraparound(self):
        _test(self._test_wraparound)


    def _test_wraparound(self, channel_count, chunk_type):

        b = AudioInputBuffer(channel_count, 2, 10, chunk_type)

        write(b, 1, 18)
        c = self.assert_chunk(b, 1, 10)
        b.free_chunk(c)

        write(b, 19, 22)
        c = self.assert_chunk(b, 11, 20)
        b.free_chunk(c)

        write(b, 23, 40)
        c = self.assert_chunk(b, 21, 30)
        b.free_chunk(c)

        c = self.assert_chunk(b, 31, 40)
        b.free_chunk(c)


    def test_empty_writes(self):
        _test(self._test_empty_writes)


    def _test_empty_writes(self, channel_count, chunk_type):

        b = AudioInputBuffer(channel_count, 1, 4, chunk_type)

        # Write empty data array.
        b.write(bytearray())
        self.assert_empty(b)

        # Get nonempty data array of same size as buffer.
        data = get_raw_sample_data(b, 1, 4)

        # Write zero bytes of nonempty array.
        b.write(data, 0)
        self.assert_empty(b)

        # Write nonempty array and check that there's no input overflow.
        b.write(data)
        self.assert_size(b, 1)
        self.assert_chunk(b, 1, 4)


    def test_partial_writes(self):
        _test(self._test_partial_writes)


    def _test_partial_writes(self, channel_count, chunk_type):

        b = AudioInputBuffer(channel_count, 1, 4, chunk_type)

        # Get nonempty data array of same size as buffer.
        data = get_raw_sample_data(b, 1, 4)

        # Write first two frames only.
        b.write(data, 2)
        self.assert_empty(b)

        # Complete chunk.
        write(b, 3, 4)
        self.assert_size(b, 1)
        self.assert_chunk(b, 1, 4)


    def test_write_size_none(self):
        _test(self._test_write_size_none)


    def _test_write_size_none(self, channel_count, chunk_type):

        b = AudioInputBuffer(channel_count, 1, 4, chunk_type)

        # Get nonempty data array of same size as buffer.
        data = get_raw_sample_data(b, 1, 4)

        b.write(data, None)
        self.assert_size(b, 1)
        self.assert_chunk(b, 1, 4)


    def test_get_chunk_from_empty_buffer(self):
        _test(self._test_get_chunk_from_empty_buffer)


    def _test_get_chunk_from_empty_buffer(self, channel_count, chunk_type):
        b = AudioInputBuffer(channel_count, 1, 4, chunk_type)
        c = b.get_chunk()
        self.assertIsNone(c)


    def test_overflow_exception(self):
        _test(self._test_overflow_exception)


    def _test_overflow_exception(self, channel_count, chunk_type):

        b = AudioInputBuffer(channel_count, 1, 4, chunk_type)

        write(b, 1, 3)
        self.assert_empty(b)

        self.assert_raises(AudioInputBufferOverflow, write, b, 4, 5)


    def assert_empty(self, b):
        self.assert_size(b, 0)


    def assert_size(self, b, size):
        self.assertEqual(b.size, size)


    def assert_chunk(self, b, start_value, end_value):

        samples = get_samples(b.channel_count, start_value, end_value)

        format = b.chunk_type.input_sample_format
        expected_samples = format.normalize_samples(samples)

        c = b.get_chunk()
        self.assertEqual(c.channel_count, b.channel_count)
        self.assert_arrays_equal(c.samples, expected_samples)

        return c


def create_buffer(capacity, chunk_size, channel_count, chunk_type):
    return AudioInputBuffer(
        capacity, chunk_size, channel_count, chunk_type)


def _test(method):
    for channel_count in CHANNEL_COUNTS:
        for chunk_type in CHUNK_TYPES:
            method(channel_count, chunk_type)


def write(buffer, start_value, end_value):
    data = get_raw_sample_data(buffer, start_value, end_value)
    buffer.write(data)


def get_raw_sample_data(buffer, start_value, end_value):
    samples = get_samples(buffer.channel_count, start_value, end_value)
    format = buffer.chunk_type.input_sample_format
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
