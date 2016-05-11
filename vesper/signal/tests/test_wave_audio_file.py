import io
import os.path

import numpy as np

from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType, WaveAudioFileReader
from vesper.tests.test_case import TestCase
import vesper.signal.audio_file_utils as audio_file_utils
import vesper.signal.tests.utils as utils


_TEST_FILE_DIR_PATH = os.path.join(
    os.path.dirname(__file__), 'data', 'Sound Files')


class WaveAudioFileTests(TestCase):


    def test_reader(self):
        
        cases = [
            ('One Channel.wav', 1, 100, 22050, np.int16),
            ('Two Channels.wav', 2, 10, 24000, np.int16),
            ('Four Channels.wav', 4, 100, 22050, np.int16)
        ]
        
        for file_name, num_channels, length, sample_rate, dtype in cases:
            
            file_path = os.path.join(_TEST_FILE_DIR_PATH, file_name)
            
            self.assertTrue(WaveAudioFileType.is_supported_file(file_path))
            
            # Test reader constructed from file.
            with WaveAudioFileType.reader_class(file_path) as reader:
                self._test_reader(
                    reader, file_path, WaveAudioFileType, num_channels, length,
                    sample_rate, dtype)
            
            # Test reader constructed from file contents.
            with open(file_path, 'rb') as file_:
                data = file_.read()
            file_ = io.BytesIO(data)
            with WaveAudioFileType.reader_class(file_) as reader:
                self._test_reader(
                    reader, None, WaveAudioFileType, num_channels, length,
                    sample_rate, dtype)
            
            # Test reading with `audio_file_utils.read_file`.
            self._test_read_file(
                file_path, num_channels, length, sample_rate, dtype)
                
            
    def _test_reader(
                self, reader, file_path, file_type, num_channels, length,
                sample_rate, dtype):
        
            self.assertEqual(reader.file_path, file_path)
            self.assertEqual(reader.file_type, WaveAudioFileType)
            self.assertEqual(reader.num_channels, num_channels)
            self.assertEqual(reader.length, length)
            self.assertEqual(reader.sample_rate, sample_rate)
            self.assertEqual(reader.dtype, dtype)
            
            expected = utils.create_samples(
                (num_channels, length), factor=1000, dtype=dtype)
            
            # all samples
            samples = reader.read()
            self._assert_samples(samples, expected)
            
            # samples from frame 5 on
            samples = reader.read(start_index=5)
            self._assert_samples(samples, expected[:, 5:])
            
            # a couple of segments
            for start_index, length in [(0, 5), (5, 5)]:
                samples = reader.read(start_index, length)
                stop_index = start_index + length
                self._assert_samples(
                    samples, expected[:, start_index:stop_index])
            
            
    def _assert_samples(self, samples, expected):
        self.assertEqual(samples.shape, expected.shape)
        self.assertEqual(samples.dtype, expected.dtype)
        utils.assert_arrays_equal(samples, expected)


    def _test_read_file(
            self, file_path, num_channels, length, sample_rate, dtype):
        
        samples, sample_rate_ = audio_file_utils.read_audio_file(file_path)
        
        self.assertEqual(sample_rate_, sample_rate)
        
        expected = utils.create_samples(
            (num_channels, length), factor=1000, dtype=dtype)
        self._assert_samples(samples, expected)


    def test_mono_1d_reads(self):
        
        cases = [
            ('One Channel.wav', 1, 100, np.int16),
            ('Two Channels.wav', 2, 10, np.int16)
        ]
        
        for file_name, num_channels, length, dtype in cases:
            file_path = _create_test_file_path(file_name)
            samples, _ = \
                audio_file_utils.read_audio_file(file_path, mono_1d=True)
            shape = (length,) if num_channels == 1 else (num_channels, length)
            expected = utils.create_samples(shape, factor=1000, dtype=dtype)
            self._assert_samples(samples, expected)


    def test_nonexistent_file_error(self):
        self._assert_raises(ValueError, WaveAudioFileReader, 'Nonexistent')
        
        
    def test_non_wav_file_error(self):
        file_path = _create_test_file_path('Empty')
        self._assert_raises(
            UnsupportedAudioFileError, WaveAudioFileReader, file_path)
        
        
    def test_empty_wav_file_error(self):
        file_path = _create_test_file_path('Empty.wav')
        self._assert_raises(OSError, WaveAudioFileReader, file_path)
        
        
    def test_closed_wav_file_read_error(self):
        file_path = _create_test_file_path('One Channel.wav')
        reader = WaveAudioFileReader(file_path)
        reader.close()
        self._assert_raises(OSError, reader.read)

        
    def test_out_of_range_wav_file_read_errors(self):
        
        file_path = _create_test_file_path('One Channel.wav')
        
        cases = [
            (-10, None),
            (1000, None),
            (0, 1000)
        ]
        
        for start_index, length in cases:
            reader = WaveAudioFileReader(file_path)
            self._assert_raises(ValueError, reader.read, start_index, length)
        

    def test_truncated_wav_file_error(self):
        file_path = _create_test_file_path('Truncated.wav')
        reader = WaveAudioFileReader(file_path)
        self._assert_raises(OSError, reader.read)
        
        
def _create_test_file_path(file_name):
    dir_path = os.path.dirname(__file__)
    return os.path.join(dir_path, 'data', 'Sound Files', file_name)
