from pathlib import Path
import os.path

import numpy as np

from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils


_DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)
_TEST_FILE_NAME = 'test.wav'

_TEST_CASES = [
    ('One Channel.wav', 1, 100, 22050),
    ('Two Channels.wav', 2, 10, 24000),
    ('Four Channels.wav', 4, 100, 22050)
]

_EXPECTED_SAMPLE_SIZE = 16
_EXPECTED_COMPRESSION_TYPE = 'NONE'
_EXPECTED_COMPRESSION_NAME = 'not compressed'


class AudioFileUtilsTests(TestCase):


    def test_is_wave_file_path(self):
        
        positives = [
            'bobo.wav',
            'harold/bobo.wav',
            '/Users/harold/bobo.wav'
        ]
        
        negatives = [
            'bobo',
            'bobo.txt',
            'harold/bobo.txt',
            '/Users/harold/bobo.txt'
        ]
        
        f = audio_file_utils.is_wave_file_path
        
        for p in positives:
            self.assertTrue(f(p))
            self.assertTrue(f(Path(p)))
            
        for p in negatives:
            self.assertFalse(f(p))
            self.assertFalse(f(Path(p)))
            

    def test_is_wave_file_path_errors(self):
        f = audio_file_utils.is_wave_file_path
        self._assert_raises(TypeError, f, 10)
        self._assert_raises(TypeError, f, [])
        self._assert_raises(TypeError, f, {})
        
        
    def test_get_wave_file_info(self):
        
        for file_name, expected_num_channels, expected_length, \
                expected_sample_rate in _TEST_CASES:
            
            path = _create_file_path(file_name)
            
            info = audio_file_utils.get_wave_file_info(path)
                
            self.assertEqual(info.num_channels, expected_num_channels)
            self.assertEqual(info.length, expected_length)
            self.assertEqual(info.sample_size, _EXPECTED_SAMPLE_SIZE)
            self.assertEqual(info.sample_rate, expected_sample_rate)
            self.assertEqual(info.compression_type, _EXPECTED_COMPRESSION_TYPE)
            self.assertEqual(info.compression_name, _EXPECTED_COMPRESSION_NAME)


    def test_read_wave_file(self):
        for case in _TEST_CASES:
            self._assert_wave_file(*case)
            
            
    def _assert_wave_file(
            self, file_name, expected_num_channels, expected_length,
            expected_sample_rate):
        
        path = _create_file_path(file_name)
        
        samples, sample_rate = audio_file_utils.read_wave_file(path)
        
        self._assert_samples(samples, expected_num_channels, expected_length)
        self.assertEqual(sample_rate, expected_sample_rate)
            
            
    def _assert_samples(self, samples, expected_num_channels, expected_length):
        
        self.assertEqual(samples.shape[0], expected_num_channels)
        self.assertEqual(samples.shape[1], expected_length)
        
        expected_samples = _create_samples(
            expected_num_channels, expected_length)
        self.assertTrue(np.all(samples == expected_samples))
        
        
    def test_write_wave_file(self):
        
        path = _create_file_path(_TEST_FILE_NAME)
        
        for _, num_channels, length, sample_rate in _TEST_CASES:
            
            samples = _create_samples(num_channels, length)
            audio_file_utils.write_wave_file(path, samples, sample_rate)
            
            try:
                self._assert_wave_file(
                    _TEST_FILE_NAME, num_channels, length, sample_rate)
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
            
            
    def test_write_empty_wave_file_in_parts(self):
        
        sample_size = 16
        frame_count = 0
        
        cases = [
            (1, 24000),
            (2, 24000),
            (1, 48000)
        ]
        
        for channel_count, sample_rate in cases:
            
            path = _create_file_path(_TEST_FILE_NAME)
        
            audio_file_utils.write_empty_wave_file(
                path, channel_count, sample_rate, sample_size)

            try:
                self._assert_wave_file(
                    _TEST_FILE_NAME, channel_count, frame_count, sample_rate)
            finally:
                os_utils.delete_file(path)
                
                
    def test_write_wave_file_samples(self):
        
        channel_counts = (1, 2)
        sample_rate = 24000
        sample_size = 16
        file_size = 20
        
        cases = [
            
            # in-order writes
            [(0, 10), (10, 5), (15, 5)],
            
            # out-of-order writes
            [(0, 5), (20, 10), (5, 10), (15, 5)]

        ]

        path = _create_file_path(_TEST_FILE_NAME)
        
        for writes in cases:
            
            for channel_count in channel_counts:
            
                audio_file_utils.write_empty_wave_file(
                    path, channel_count, sample_rate, sample_size)
                
                for start_index, frame_count in writes:
                    
                    samples = _create_samples(channel_count, frame_count)
                    samples += start_index
                    
                    audio_file_utils.write_wave_file_samples(
                        path, start_index, samples)
                    
                try:
                    self._assert_wave_file(
                        _TEST_FILE_NAME, channel_count, file_size, sample_rate)
                finally:
                    os_utils.delete_file(path)
                    
                
def _create_file_path(file_name):
    return os.path.join(_DATA_DIR_PATH, file_name)


def _create_samples(num_channels, length):
    samples = np.arange(length)
    return np.vstack([samples + i * 1000 for i in range(num_channels)])
