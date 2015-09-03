import os.path

import numpy as np

import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils

from test_case import TestCase


_DATA_DIR_PATH = r'data\audio_file_utils Test Files'
_TEST_FILE_NAME = 'test.wav'

_TEST_CASES = [
    ('One Channel.wav', 1, 22050, 100),
    ('Two Channels.wav', 2, 24000, 10),
    ('Four Channels.wav', 4, 22050, 100)
]

_EXPECTED_SAMPLE_SIZE = 16
_EXPECTED_COMPRESSION_TYPE = 'NONE'


class AudioFileUtilsTests(TestCase):


    def test_get_wave_file_info(self):
        
        for file_name, expected_num_channels, expected_sample_rate, \
                expected_num_frames in _TEST_CASES:
            
            path = _create_file_path(file_name)
            
            num_channels, sample_size, sample_rate, num_frames, \
                compression_type = audio_file_utils.get_wave_file_info(path)
                
            self.assertEqual(num_channels, expected_num_channels)
            self.assertEqual(sample_size, _EXPECTED_SAMPLE_SIZE)
            self.assertEqual(sample_rate, expected_sample_rate)
            self.assertEqual(num_frames, expected_num_frames)
            self.assertEqual(compression_type, _EXPECTED_COMPRESSION_TYPE)


    def test_read_wave_file(self):
        for case in _TEST_CASES:
            self._assert_wave_file(*case)
            
            
    def _assert_wave_file(
            self, file_name, expected_num_channels, expected_sample_rate,
            expected_num_frames):
        
        path = _create_file_path(file_name)
        
        samples, sample_rate = audio_file_utils.read_wave_file(path)
        
        self._assert_samples(
            samples, expected_num_channels, expected_num_frames)
        self.assertEqual(sample_rate, expected_sample_rate)
            
            
    def _assert_samples(
            self, samples, expected_num_channels, expected_num_frames):
        
        self.assertEqual(samples.shape[0], expected_num_channels)
        self.assertEqual(samples.shape[1], expected_num_frames)
        
        expected_samples = _create_samples(
            expected_num_channels, expected_num_frames)
        self.assertTrue(np.all(samples == expected_samples))
        
        
    def test_write_wave_file(self):
        
        path = _create_file_path(_TEST_FILE_NAME)
        
        for _, num_channels, sample_rate, num_frames in _TEST_CASES:
            
            samples = _create_samples(num_channels, num_frames)
            audio_file_utils.write_wave_file(path, samples, sample_rate)
            
            try:
                self._assert_wave_file(
                    _TEST_FILE_NAME, num_channels, sample_rate, num_frames)
            finally:
                os_utils.delete_file(path)
                
                
    def test_copy_wave_file_channel(self):
        
        cases = [
            ('One Channel.wav', 0)
        ]
        
        for input_file_name, channel_num in cases:
            
            self._test_copy_wave_file_channel_aux(
                input_file_name, channel_num)
            
            self._test_copy_wave_file_channel_aux(
                input_file_name, channel_num, chunk_size=17)
            
            
    def _test_copy_wave_file_channel_aux(
            self, input_file_name, channel_num, chunk_size=None):
        
        input_file_path = _create_file_path(input_file_name)
        output_file_path = _create_file_path(_TEST_FILE_NAME)
        
        expected_samples, expected_sample_rate = \
            audio_file_utils.read_wave_file(input_file_path)
        expected_samples = expected_samples[channel_num]
            
        try:
            
            if chunk_size is None:
                audio_file_utils.copy_wave_file_channel(
                    input_file_path, channel_num, output_file_path)
                
            else:
                audio_file_utils.copy_wave_file_channel(
                    input_file_path, channel_num, output_file_path,
                    chunk_size)
            
            samples, sample_rate = \
                audio_file_utils.read_wave_file(output_file_path)
                
            self.assertEqual(samples.shape[0], 1)
            self.assertEqual(samples.shape[1], len(expected_samples))
            self.assertEqual(sample_rate, expected_sample_rate)
            self.assertTrue(all(samples[0] == expected_samples))
            
        finally:
            os_utils.delete_file(output_file_path)
            
            
def _create_file_path(file_name):
    return os.path.join(_DATA_DIR_PATH, file_name)


def _create_samples(num_channels, num_frames):
    samples = np.arange(num_frames)
    return np.vstack(samples + i * 1000 for i in range(num_channels))

