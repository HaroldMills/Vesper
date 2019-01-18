import numpy as np


from vesper.tests.test_case import TestCase
from vesper.util.sample_buffer import SampleBuffer


class SampleBufferTests(TestCase):
    
    
    def test_init(self):
        b = SampleBuffer(np.int64)
        self.assertEqual(b.dtype, np.int64)
        self._assert_buffer(b, 0, 0, 0)
        
        
    def _assert_buffer(self, buffer, write_index, read_index, length):
        self.assertEqual(buffer.write_index, write_index)
        self.assertEqual(buffer.read_index, read_index)
        self.assertEqual(len(buffer), length)


    def test_zero_length_write(self):
        b = SampleBuffer(np.float64)
        b.write(np.array([]))
        self._assert_buffer(b, 0, 0, 0)
        
        
    def test_zero_length_read(self):
        b = SampleBuffer(np.float64)
        result = b.read(0)
        self._assert_arrays_equal(result, np.array([], np.float64))
        self._assert_buffer(b, 0, 0, 0)
        
        
    def test_read_all(self):
        b = SampleBuffer(np.int64)
        b.write(np.arange(0, 10))
        b.write(np.arange(10, 20))
        self._assert_arrays_equal(b.read(), np.arange(0, 20))
        self.assertEqual(b.read_index, 20)
                
        
    def test_simple_write_read(self):
        b = SampleBuffer(np.int64)
        b.write(np.arange(0, 10))
        b.write(np.arange(10, 20))
        self._assert_arrays_equal(b.read(20), np.arange(0, 20))
                
        
    def test_write_read(self):
        b = SampleBuffer(np.int64)
        b.write(np.arange(0, 10))
        b.write(np.arange(10, 20))
        self._assert_buffer(b, 20, 0, 20)
        self._assert_arrays_equal(b.read(7), np.arange(0, 7))
        self._assert_buffer(b, 20, 7, 13)
        self._assert_arrays_equal(b.read(7), np.arange(7, 14))
        self._assert_buffer(b, 20, 14, 6)
        self._assert_arrays_equal(b.read(6), np.arange(14, 20))
        self._assert_buffer(b, 20, 20, 0)
        
        
    def test_simple_increments(self):
        b = SampleBuffer(np.int64)
        b.increment(10)
        b.increment(20)
        self._assert_buffer(b, 0, 30, 0)
        
        
    def test_write_read_inc(self):
        
        b = SampleBuffer(np.int64)
        
        b.increment(5)
        b.write(np.arange(0, 10))
        self._assert_arrays_equal(b.read(2), np.arange(5, 7))
        self._assert_buffer(b, 10, 7, 3)
        
        b.write(np.arange(10, 20))
        self._assert_arrays_equal(b.read(5), np.arange(7, 12))
        self._assert_buffer(b, 20, 12, 8)

        b.increment(5)
        self._assert_arrays_equal(b.read(3), np.arange(17, 20))
        self._assert_buffer(b, 20, 20, 0)
        
        b.increment(5)
        self._assert_buffer(b, 20, 25, 0)
        
        
    def test_read_with_inc(self):
        b = SampleBuffer(np.int64)
        b.write(np.arange(0, 20))
        self._assert_arrays_equal(b.read(10, 5), np.arange(0, 10))
        self._assert_arrays_equal(b.read(10, 5), np.arange(5, 15))
        self._assert_arrays_equal(b.read(10, 5), np.arange(10, 20))
