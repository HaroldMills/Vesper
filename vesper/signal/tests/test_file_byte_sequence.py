from pathlib import Path
import unittest

from vesper.signal.tests.byte_sequence_tests import ByteSequenceTests
from vesper.signal.file_byte_sequence import FileByteSequence
from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))
_TEST_FILE_PATH = _DATA_DIR_PATH / 'Bytes 00-FF.dat'


class FileByteSequenceTests(TestCase, ByteSequenceTests):


    def __init__(self, *args, **kwargs):
        self.seq = FileByteSequence(_TEST_FILE_PATH)
        super().__init__(*args, **kwargs)


    def test_open_reads(self):

        seq = self.seq
        self.assertFalse(seq.is_open)

        seq.open()
        self.assertTrue(seq.is_open)

        self.test_read()
        self.assertTrue(seq.is_open)

        seq.close()
        self.assertFalse(seq.is_open)


    def test_context_manager_reads(self):

        self.assertFalse(self.seq.is_open)

        with self.seq as seq:
            self.assertTrue(seq.is_open)
            self.test_read()
            self.assertTrue(seq.is_open)

        self.assertFalse(self.seq.is_open)


    def test_file_errors(self):

        cases = (
            '/nonexistent.wav',       # nonexistent
            '/'                       # not a file
        )

        for path in cases:
            path = Path(path)
            self.assert_raises(Exception, FileByteSequence, path)


if __name__ == '__main__':
    unittest.main()
