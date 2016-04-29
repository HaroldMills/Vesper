"""Module containing class `WaveAudioFileType`."""


import six
import wave

from vesper.util.bunch import Bunch


_WAVE_FILE_NAME_EXTENSION = '.wav'


class WaveAudioFileType(object):
    
    
    @property
    def read_only(self):
        return False
    
    
    # RESUME: Maybe we shouldn't support file-like objects initially
    # as arguments to these functions, only file paths?
    
    def is_recognized_file(self, file_):
        if isinstance(file_, six.string_types):
            if not file_.endswith(_WAVE_FILE_NAME_EXTENSION):
                return 
    
    
    def _get_file_info(self, file_):
        (num_channels, sample_width, sample_rate, length, compression_type,
            compression_name) = reader.getparams()
        info = Bunch(
            num_channels=num_channels,
            sample_size=sample_width * 8,
            sample_rate=sample_rate,
            length=length)

        
    def get_file_info(self, file_):
        reader = wave.open(file_, 'rb')
        
        
    def read_file(self, file_):
        pass
    
    
    def write_file(self, file_, sound, info):
        pass
    
    
    def open_file(self, file_, mode='r', info=None):
        pass
        