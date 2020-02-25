import os
import random

import numpy as np

from vesper.old_bird.recording_reader import RecordingReader
from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)
_NUM_RECORDING_FILES = 3
_RECORDING_FILE_LENGTH = 10
_NUM_RECORDING_CHANNELS = 2
_NUM_READ_TEST_CASES = 100


class AddOldBirdClipStartIndicesTests(TestCase):


    def test_reader(self):
        
        files = [_create_file_bunch(i) for i in range(_NUM_RECORDING_FILES)]
        reader = RecordingReader(files)
        
        recording_length = _NUM_RECORDING_FILES * _RECORDING_FILE_LENGTH
        
        for _ in range(_NUM_READ_TEST_CASES):
            
            channel_num = random.randrange(_NUM_RECORDING_CHANNELS)
            start_index = random.randrange(recording_length)
            length = random.randrange(recording_length - start_index)
            
            expected = _get_expected_samples(channel_num, start_index, length)
            actual = reader.read_samples(channel_num, start_index, length)
            
#             print(channel_num, start_index, length)
#             print(actual)
#             print()
            
            self._assert_arrays_equal(actual, expected)
            
                    
def _create_file_bunch(i):
    return Bunch(
        path=_create_file_path(f'recording_file_{i}.wav'),
        start_index=_RECORDING_FILE_LENGTH * i,
        length=_RECORDING_FILE_LENGTH)


def _create_file_path(file_name):
    return os.path.join(_DATA_DIR_PATH, file_name)


def _get_expected_samples(channel_num, start_index, length):
    return np.arange(start_index, start_index + length) + 1000 * channel_num
