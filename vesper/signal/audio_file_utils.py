"""Utility functions pertaining to audio files."""


import os.path

from vesper.signal.time_axis import TimeAxis
from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType


_AUDIO_FILE_TYPES = (
    WaveAudioFileType,
)


def get_audio_file_type(file_path):
    
    """Gets the audio file type for the specified file."""
    
    if not os.path.exists(file_path):
        raise ValueError(f'File "{file_path}" does not exist.')
    
    for file_type in _AUDIO_FILE_TYPES:
        if file_type.is_supported_file(file_path):
            return file_type
        
    # If we get here, the file was not recognized by any audio file type.
    return None
