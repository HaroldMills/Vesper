"""Utility functions pertaining to audio files."""


import os.path

from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType


_AUDIO_FILE_TYPES = (
    WaveAudioFileType,
)


def get_file_type(file_path):
    
    if not os.path.exists(file_path):
        raise ValueError('File "{}" does not exist.'.format(file_path))
    
    for file_type in _AUDIO_FILE_TYPES:
        if file_type.is_supported_file(file_path):
            return file_type
        
    # If we get here, the file was not recognized by any audio file type.
    return None
    
    
def _get_file_type(file_path):
    
    file_type = get_file_type(file_path)
    
    if file_type is None:
        raise UnsupportedAudioFileError(
            'File "{}" is not of any recognized audio file type.'.format(
                file_path))
        
    else:
        return file_type
        
        
def read_file(file_path, mono_1d=False):
    file_type = _get_file_type(file_path)
    with file_type.reader_class(file_path, mono_1d=mono_1d) as reader:
        samples = reader.read()
        sample_rate = reader.sample_rate
        return (samples, sample_rate)
