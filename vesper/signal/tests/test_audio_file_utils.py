# import numpy as np

# from vesper.signal.array_signal import ArraySignal
# from vesper.signal.multichannel_array_signal import MultichannelArraySignal
# from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType
from vesper.tests.test_case import TestCase
import vesper.signal.audio_file_utils as audio_file_utils
import vesper.signal.tests.utils as utils


class AudioFileUtilsTests(TestCase):


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
        self.assert_raises(cls, function, file_path)
