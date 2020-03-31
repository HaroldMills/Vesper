from vesper.tests.test_case import TestCase
from vesper.util.byte_buffer import ByteBuffer


class ByteBufferTests(TestCase):


    def test_initializer(self):
        
        b = ByteBuffer(10)
        self.assertEqual(len(b.bytes), 10)
        self.assertEqual(b.offset, 0)
        
        b = ByteBuffer(bytearray(12))
        self.assertEqual(len(b.bytes), 12)
        self.assertEqual(b.offset, 0)

        
    def test_reads_and_writes(self):
        self._test_reads_and_writes(ByteBuffer(14))
        self._test_reads_and_writes(ByteBuffer(bytearray(14)))
        
        
    def _test_reads_and_writes(self, b):
        
        b.write_bytes(b'test')
        self.assertEqual(b.offset, 4)
        
        b.write_value(17, '<I')
        self.assertEqual(b.offset, 8)
        
        b.write_value(18, '<H', 12)
        self.assertEqual(b.offset, 14)
        
        b.write_value(1.5, '<f', 8)
        self.assertEqual(b.offset, 12)
        
        b.offset = 0
        
        bytes_ = b.read_bytes(4)
        self.assertEqual(bytes_, b'test')
        self.assertEqual(b.offset, 4)
 
        value = b.read_value('<I')
        self.assertEqual(value, 17)
        self.assertEqual(b.offset, 8)
        
        value = b.read_value('<H', 12)
        self.assertEqual(value, 18)
        self.assertEqual(b.offset, 14)
        
        value = b.read_value('<f', 8)
        self.assertEqual(value, 1.5)
        self.assertEqual(b.offset, 12)
