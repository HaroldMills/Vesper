import numpy as np

from vesper.signal.array_signal import ArraySignal
from vesper.signal.multichannel_array_signal import MultichannelArraySignal
from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType
from vesper.tests.test_case import TestCase
import vesper.signal.audio_file_utils as audio_file_utils
import vesper.signal.tests.utils as utils


class WaveAudioFileTests(TestCase):


    def test_get_audio_file_type(self):
        
        cases = [
            ('One Channel.wav', WaveAudioFileType),
            ('Two Channels.wav', WaveAudioFileType),
            ('Empty', None)
        ]
        
        for file_name, expected in cases:
            file_path = utils.create_test_audio_file_path(file_name)
            file_type = audio_file_utils.get_audio_file_type(file_path)
            self.assertEqual(file_type, expected)
            
            
    def test_get_audio_file_type_error(self):
        function = audio_file_utils.get_audio_file_type
        self._assert_function_raises(ValueError, function, 'Nonexistent')
        
        
    def _assert_function_raises(self, cls, function, file_name):
        file_path = utils.create_test_audio_file_path(file_name)
        self._assert_raises(cls, function, file_path)
        
        
    def test_create_multichannel_array_signal(self):
        
        cases = [
            ('One Channel.wav', 1, 100, 22050, np.int16),
            ('Two Channels.wav', 2, 10, 24000, np.int16),
            ('Four Channels.wav', 4, 100, 22050, np.int16)
        ]
        
        for file_name, num_channels, length, sample_rate, dtype in cases:
            
            file_path = utils.create_test_audio_file_path(file_name)
            
            audio = audio_file_utils.create_multichannel_array_signal(file_path)
            
            self.assertIsInstance(audio, MultichannelArraySignal)
            self.assertEqual(len(audio), num_channels)
            self.assertEqual(audio.time_axis.length, length)
            self.assertEqual(audio.time_axis.sample_rate, sample_rate)
            self.assertEqual(audio.dtype, dtype)
            
            expected = utils.create_samples(
                (num_channels, length), factor=1000, dtype=dtype)
            utils.assert_arrays_equal(audio[:], expected, strict=True)
        
        
    def test_create_multichannel_array_signal_errors(self):
        
        function = audio_file_utils.create_multichannel_array_signal

        # Nonexistent file.
        self._assert_function_raises(ValueError, function, 'Nonexistent')
        
        # Unsupported file.
        self._assert_function_raises(
            UnsupportedAudioFileError, function, 'Empty')
        
        
    def test_create_array_signal(self):
        
        cases = [
            ('One Channel.wav', 100, 22050, np.int16),
        ]
        
        for file_name, length, sample_rate, dtype in cases:
            
            file_path = utils.create_test_audio_file_path(file_name)
            
            audio = audio_file_utils.create_array_signal(file_path)
            
            self.assertIsInstance(audio, ArraySignal)
            self.assertEqual(len(audio), length)
            self.assertEqual(audio.time_axis.sample_rate, sample_rate)
            self.assertEqual(audio.dtype, dtype)
            
            expected = utils.create_samples((length,), factor=1000, dtype=dtype)
            utils.assert_arrays_equal(audio[:], expected, strict=True)


    def test_create_array_signal_errors(self):
        
        function = audio_file_utils.create_array_signal

        # Nonexistent file.
        self._assert_function_raises(ValueError, function, 'Nonexistent')
        
        # Unsupported file.
        self._assert_function_raises(
            UnsupportedAudioFileError, function, 'Empty')
        
        # Multichannel file.
        self._assert_function_raises(ValueError, function, 'Two Channels.wav')
        
        
