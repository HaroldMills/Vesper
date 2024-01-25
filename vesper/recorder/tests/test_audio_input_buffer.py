from vesper.recorder.audio_input_buffer import (
    AudioInputBuffer, AudioInputBufferOverflow)
from vesper.tests.test_case import TestCase


class AudioInputBufferTests(TestCase):


    def test_init(self):
         b = AudioInputBuffer(4, 5, 2)
         self.assertEqual(b.capacity, 4)
         self.assertEqual(b.chunk_size, 5)
         self.assertEqual(b.sample_frame_size, 2)
         self.assert_empty(b)


    def test_write_read(self):
         
        b = AudioInputBuffer(3, 5, 2)
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

        b = AudioInputBuffer(2, 5, 2)

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

        b = AudioInputBuffer(1, 3, 2)

        # Write empty array.
        b.write(bytearray())
        self.assert_empty(b)

        # Write zero bytes of two-byte array.
        b.write(ba(1, 2), 0)
        self.assert_empty(b)

        b.write(ba(1, 6))
        self.assert_size(b, 1)
        c = self.assert_chunk(b, 1, 6)
        b.free_chunk(c)


    def test_partial_writes(self):

        b = AudioInputBuffer(1, 3, 2)

        # Write one frame of two-frame array.
        b.write(ba(1, 4), 1)
        self.assert_empty(b)

        write(b, 3, 6)
        self.assert_size(b, 1)
        c = self.assert_chunk(b, 1, 6)
        b.free_chunk(c)


    def test_write_size_none(self):

        b = AudioInputBuffer(1, 3, 2)

        b.write(ba(1, 6), None)
        self.assert_size(b, 1)
        self.assert_chunk(b, 1, 6)


    def test_empty_exception(self):
        b = AudioInputBuffer(1, 3, 2)
        c = b.get_chunk()
        self.assertIsNone(c)


    def test_overflow_exception(self):

        b = AudioInputBuffer(1, 3, 2)

        write(b, 1, 4)
        self.assert_empty(b)

        self.assert_raises(AudioInputBufferOverflow, write, b, 5, 8)


    def assert_empty(self, b):
        self.assert_size(b, 0)


    def assert_size(self, b, size):
        self.assertEqual(b.size, size)


    def assert_chunk(self, b, start_value, end_value):
        actual = b.get_chunk()
        expected = ba(start_value, end_value)
        self.assertEqual(actual, expected)
        return actual


def write(buffer, start_value, end_value):
    data = ba(start_value, end_value)
    buffer.write(data)
    

def ba(start_value, end_value):
     return bytearray(range(start_value, end_value + 1))
