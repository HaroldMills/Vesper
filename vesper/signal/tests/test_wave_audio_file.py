import io

import numpy as np

from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType, WaveAudioFileReader
from vesper.tests.test_case import TestCase
import vesper.signal.audio_file_utils as audio_file_utils
import vesper.signal.tests.utils as utils


class WaveAudioFileTests(TestCase):


    # def test_reader(self):
    #
    #     cases = [
    #         ('One Channel.wav', 1, 100, 22050, np.int16),
    #         ('Two Channels.wav', 2, 10, 24000, np.int16),
    #         ('Four Channels.wav', 4, 100, 22050, np.int16)
    #     ]
    #
    #     for file_name, num_channels, length, sample_rate, dtype in cases:
    #
    #         file_path = utils.create_test_audio_file_path(file_name)
    #
    #         self.assertTrue(WaveAudioFileType.is_supported_file(file_path))
    #
    #         # Test reader constructed from file.
    #         with WaveAudioFileType.reader_class(file_path) as reader:
    #             self._test_reader(
    #                 reader, file_path, WaveAudioFileType, num_channels, length,
    #                 sample_rate, dtype)
    #
    #         # Test reader constructed from file contents.
    #         with open(file_path, 'rb') as file_:
    #             data = file_.read()
    #         file_ = io.BytesIO(data)
    #         with WaveAudioFileType.reader_class(file_) as reader:
    #             self._test_reader(
    #                 reader, None, WaveAudioFileType, num_channels, length,
    #                 sample_rate, dtype)
    #
    #         self._test_create_multichannel_array_signal(
    #             file_path, num_channels, length, sample_rate, dtype)
    #
    #
    # def _test_reader(
    #             self, reader, file_path, file_type, num_channels, length,
    #             sample_rate, dtype):
    #
    #         self.assertEqual(reader.file_path, file_path)
    #         self.assertEqual(reader.file_type, WaveAudioFileType)
    #         self.assertEqual(reader.num_channels, num_channels)
    #         self.assertEqual(reader.length, length)
    #         self.assertEqual(reader.sample_rate, sample_rate)
    #         self.assertEqual(reader.dtype, dtype)
    #
    #         expected = utils.create_samples(
    #             (num_channels, length), factor=1000, dtype=dtype)
    #
    #         # all samples
    #         samples = reader.read()
    #         utils.assert_arrays_equal(samples, expected, strict=True)
    #
    #         # samples from frame 5 on
    #         samples = reader.read(start_index=5)
    #         utils.assert_arrays_equal(samples, expected[:, 5:], strict=True)
    #
    #         # a couple of segments
    #         for start_index, length in [(0, 5), (5, 5)]:
    #             samples = reader.read(start_index, length)
    #             stop_index = start_index + length
    #             utils.assert_arrays_equal(
    #                 samples, expected[:, start_index:stop_index], strict=True)
    #
    #
    # def _test_create_multichannel_array_signal(
    #         self, file_path, num_channels, length, sample_rate, dtype):
    #
    #     audio = audio_file_utils.create_multichannel_array_signal(file_path)
    #
    #     self.assertEqual(len(audio), num_channels)
    #     self.assertEqual(audio.time_axis.length, length)
    #     self.assertEqual(audio.time_axis.sample_rate, sample_rate)
    #     self.assertEqual(audio.dtype, dtype)
    #
    #     expected = utils.create_samples(
    #         (num_channels, length), factor=1000, dtype=dtype)
    #     utils.assert_arrays_equal(audio[:], expected, strict=True)


    def test_nonexistent_file_error(self):
        self.assert_raises(ValueError, WaveAudioFileReader, 'Nonexistent')
        
        
    def test_non_wav_file_error(self):
        file_path = utils.create_test_audio_file_path('Empty')
        self.assert_raises(
            UnsupportedAudioFileError, WaveAudioFileReader, file_path)
        
        
    def test_empty_wav_file_error(self):
        file_path = utils.create_test_audio_file_path('Empty.wav')
        self.assert_raises(OSError, WaveAudioFileReader, file_path)
        
        
    def test_closed_wav_file_read_error(self):
        file_path = utils.create_test_audio_file_path('One Channel.wav')
        reader = WaveAudioFileReader(file_path)
        reader.close()
        self.assert_raises(OSError, reader.read)

        
    def test_out_of_range_wav_file_read_errors(self):
        
        file_path = utils.create_test_audio_file_path('One Channel.wav')
        
        cases = [
            (-10, None),
            (1000, None),
            (0, 1000)
        ]
        
        for start_index, length in cases:
            reader = WaveAudioFileReader(file_path)
            self.assert_raises(ValueError, reader.read, start_index, length)
        

    def test_truncated_wav_file_error(self):
        file_path = utils.create_test_audio_file_path('Truncated.wav')
        reader = WaveAudioFileReader(file_path)
        self.assert_raises(OSError, reader.read)
