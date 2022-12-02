from pathlib import Path
import unittest

from vesper.signal.tests.byte_sequence_tests import ByteSequenceTests
from vesper.signal.file_byte_sequence import FileByteSequence
from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils


DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))
TEST_FILE_PATH = DATA_DIR_PATH / 'Bytes 00-FF.dat'


class FileByteSequenceTests(TestCase, ByteSequenceTests):


    @property
    def sequence(self):
        return FileByteSequence(TEST_FILE_PATH)


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
