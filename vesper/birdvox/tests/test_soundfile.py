import os

import numpy as np

from vesper.birdvox.soundfile import SoundFile
from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils


class SoundfileTests(TestCase):


    def test_info(self):
        file_ = _open_test_audio_file()
        self.assertEqual(file_.samplerate, 24000)
        self.assertEqual(file_.channels, 1)
        self.assertEqual(len(file_), 100)
                        
                
    def test_reads(self):
        file_ = _open_test_audio_file()
        self._test_reads(file_)
        
        
    def _test_reads(self, file_):
        self._test_read(file_, 0, 10)
        self._test_read(file_, 5, 10)
        self._test_read(file_, 80, 10)
        self._test_read(file_, 75, 20)
        
        
    def _test_read(self, file_, start_index, length):
        file_.seek(start_index)
        samples = file_.read(length)
        self.assertEqual(samples.dtype, np.dtype('float64'))
        expected = _get_expected_samples(start_index, length)
        self._assert_arrays_equal(samples, expected)
        
        
    # This test verifies that PySoundFile's SoundFile seek and read
    # methods work as we expect. Commenting it out makes this module
    # not dependent on PySoundFile.
#     def test_pysoundfile_reads(self):
#         import soundfile
#         file_path = _get_test_audio_file_path()
#         file_ = soundfile.SoundFile(file_path)
#         self._test_reads(file_)
        
        
def _open_test_audio_file():
    file_path = _get_test_audio_file_path()
    return SoundFile(file_path)


def _get_test_audio_file_path():
    dir_path = test_utils.get_test_data_dir_path(__file__)
    return os.path.join(dir_path, 'test.wav')

    
def _get_expected_samples(start_index, length):
    end_index = start_index + length
    return np.arange(start_index, end_index, dtype=np.dtype('<i2')) / 32768
