import unittest
import warnings

from vesper.signal.tests.byte_sequence_tests import ByteSequenceTests
from vesper.signal.s3_byte_sequence import S3ByteSequence
from vesper.tests.test_case import TestCase


REGION_NAME = 'us-east-2'
BUCKET_NAME = 'vesper-test'
OBJECT_KEY = 'Bytes 00-FF.dat'
OBJECT_LENGTH = 256


# TODO: Look into ResourceWarning issue mentioned below. Is it safe to
# ignore the warnings?


class S3ByteSequenceTests(TestCase, ByteSequenceTests):


    @property
    def sequence(self):
        return S3ByteSequence(REGION_NAME, BUCKET_NAME, OBJECT_KEY)


    def setUp(self):

        # Without the following, the `S3ByteSequence` unit tests
        # output a ResourceWarning about an unclosed transport to the
        # console.
        warnings.filterwarnings(
            action="ignore", message="unclosed", category=ResourceWarning)


if __name__ == '__main__':
    unittest.main()
