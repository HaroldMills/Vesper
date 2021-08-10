"""Utility functions pertaining to audio files."""


import os.path

# from vesper.signal.array_signal import ArraySignal
# from vesper.signal.multichannel_array_signal import MultichannelArraySignal
from vesper.signal.time_axis import TimeAxis
from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError
from vesper.signal.wave_audio_file import WaveAudioFileType


_AUDIO_FILE_TYPES = (
    WaveAudioFileType,
)


def get_audio_file_type(file_path):
    
    """Gets the audio file type for the specified file."""
    
    if not os.path.exists(file_path):
        raise ValueError('File "{}" does not exist.'.format(file_path))
    
    for file_type in _AUDIO_FILE_TYPES:
        if file_type.is_supported_file(file_path):
            return file_type
        
    # If we get here, the file was not recognized by any audio file type.
    return None
    
    
# def create_multichannel_array_signal(
#         file_, file_type=None, reference_datetime=None):
#
#     """Creates a `MultichannelArraySignal` from an audio file."""
#
#     file_type = _get_file_type(file_, file_type)
#
#     with file_type.reader_class(file_) as reader:
#
#         samples = reader.read()
#
#         time_axis = TimeAxis(
#             length=samples.shape[1],
#             sample_rate=reader.sample_rate,
#             reference_datetime=reference_datetime)
#
#         return MultichannelArraySignal(time_axis=time_axis, samples=samples)
#
#
# def _get_file_type(file_, file_type):
#
#     if isinstance(file_, str):
#
#         if file_type is None:
#             file_type = _infer_file_type(file_)
#
#         return file_type
#
#     else:
#         # `file_` is a file-like object
#
#         if file_type is None:
#             raise ValueError('File type not specified for file-like object.')
#
#         else:
#             return file_type
#
#
# def _infer_file_type(file_path):
#
#     file_type = get_audio_file_type(file_path)
#
#     if file_type is None:
#         raise UnsupportedAudioFileError(
#             'Could not infer audio file type for file "{}".'.format(file_path))
#
#     else:
#         return file_type
#
#
# def create_array_signal(file_, file_type=None, reference_datetime=None):
#
#     """Creates an `ArraySignal` from a single-channel audio file."""
#
#     file_type = _get_file_type(file_, file_type)
#
#     with file_type.reader_class(file_) as reader:
#
#         if reader.num_channels > 1:
#
#             if isinstance(file_, str):
#                 file_path = ' "{}"'.format(file_)
#             else:
#                 file_path = ''
#
#             raise ValueError((
#                 'Cannot create array signal from multichannel file{}. '
#                 'File must have only one channel.').format(file_path))
#
#         samples = reader.read()[0]
#
#         time_axis = TimeAxis(
#             length = len(samples),
#             sample_rate=reader.sample_rate,
#             reference_datetime=reference_datetime)
#
#         return ArraySignal(time_axis=time_axis, samples=samples)
