"""Module containing class `WaveFileSignal`."""


from pathlib import Path
import wave
import os

import numpy as np

from vesper.signal.audio_file_signal import AudioFileSignal
from vesper.signal.sample_read_delegate import SampleReadDelegate
from vesper.signal.signal_error import SignalError


_WAVE_FILE_EXTENSIONS = frozenset(['.wav', '.WAV'])
    

class WaveFileSignal(AudioFileSignal):
    
    
    @staticmethod
    def is_wave_file(path):

        if isinstance(path, Path):
            extension = path.suffix
        else:
            extension = os.path.splitext(path)[1]

        return extension in _WAVE_FILE_EXTENSIONS


    def __init__(self, file, name=None):
        
        file, path = _get_file_and_path(file)

        if path is not None:
            _check_wave_file_path(path)

        self._file_text = _get_file_text(file)

        try:
            self._wave_reader = wave.open(file, 'rb')
        except:
            raise SignalError(f'Could not open {self._file_text}.')

        try:
            (channel_count, sample_width, frame_rate, frame_count,
             compression_type, compression_name) = \
                self._wave_reader.getparams()
        except:
            self._handle_error(
                f'Could not read metadata from {self._file_text}.')
        
        if compression_type != 'NONE':
            self._handle_error(
                f'{self._file_text} contains compressed data (with '
                f'compression name "{compression_name}"), which is not '
                f'supported.')
            
        sample_size = 8 * sample_width
        
        # TODO: support additional sample sizes, especially 24 bits.
        if sample_size != 8 and sample_size != 16:
            self._handle_error(
                f'{self._file_text}" contains {sample_size}-bit samples, '
                f'which are not supported.')
            
        if sample_size == 8:
            sample_type = np.uint8           # unsigned by WAVE file spec
        else:
            sample_type = np.dtype('<i2')    # little-endian by WAVE file spec

        read_delegate = _SampleReadDelegate(self)

        super().__init__(
            frame_count, frame_rate, channel_count, sample_type,
            read_delegate, name=name, file_path=path)


    def _handle_error(self, message):
        self.close()
        raise SignalError(message)


    @property
    def is_open(self):
        return self._wave_reader is not None


    def close(self):
        if self._wave_reader is not None:
            self._wave_reader.close()
            self._wave_reader = None
        

def _get_file_and_path(file):

    if isinstance(file, Path):
        return str(file), file

    elif isinstance(file, str):
        return file, Path(file)

    else:
        # `file` should be file-like object

        return file, None


def _check_wave_file_path(path):

    if not path.exists():
        raise SignalError(f'Purported WAVE file "{path}" does not exist.')

    if not path.is_file():
        raise SignalError(f'Purported WAVE file "{path}" is not a file.')

    if not WaveFileSignal.is_wave_file(path):
        raise SignalError(f'File "{path}" does not appear to be a WAVE file.')
    
        
def _get_file_text(file):

    if isinstance(file, str):
        suffix = f' "{file}"'
    else:
        suffix = ''

    return f'WAVE file{suffix}'


# def _get_file_format(channel_count, sample_size, frame_rate):
    
#     if channel_count == 1:
#         channel_string = 'Mono'
#     elif channel_count == 2:
#         channel_string = 'Stereo'
#     else:
#         channel_string = f'{channel_count}-channel'
        
#     return f'{channel_string}, {sample_size}-bit, {frame_rate} Hz WAVE'
       
       
class _SampleReadDelegate(SampleReadDelegate):
    
    
    def __init__(self, parent):
        super().__init__(True)
        self._parent = parent
        
        
    def read(self, frame_key, channel_key):
        
        if not self._parent.is_open:
            raise SignalError(
                'Attempt to read samples from closed WAVE file signal.')

        start_frame_num, end_frame_num = _get_bounds(frame_key)
        frame_count = end_frame_num - start_frame_num
        
        start_channel_num, end_channel_num = _get_bounds(channel_key)
        channel_count = end_channel_num - start_channel_num
        
        parent = self._parent

        # Set read position.
        try:
            parent._wave_reader.setpos(start_frame_num)
        except Exception:
            parent._handle_error(
                f'Could not set read position for {parent._file_text}.')

        # Read sample data.
        try:
            buffer = parent._wave_reader.readframes(frame_count)
        except Exception:
            parent._handle_error(
                f'Could not read sample data from {parent._file_text}.')
                
        # Check actual read size.
        expected_byte_count = \
            frame_count * parent.channel_count * parent.sample_type.itemsize
        if len(buffer) != expected_byte_count:
            parent._handle_error(
                f'Sample data read yielded {len(buffer)} bytes rather '
                f'than expected {expected_byte_count} bytes for '
                f'{parent._file_text}.')
            
        # Convert sample data from Python `bytes` object to
        # one-dimensional NumPy array.
        samples = np.frombuffer(buffer, dtype=parent.sample_type)
        
        # Reshape NumPy array to two dimensions.
        samples.shape = (frame_count, parent.channel_count)
        
        # Select channels if needed.
        if start_channel_num != 0 or end_channel_num != parent.channel_count:
            samples = samples[:, channel_key]
            
        # Discard shape dimensions for integer keys.
        frame_dim = _get_dim(frame_key, frame_count)
        channel_dim = _get_dim(channel_key, channel_count)
        samples.shape = frame_dim + channel_dim
                    
        return samples

        
def _get_bounds(key):

    if isinstance(key, int):
        return key, key + 1
    else:
        return key.start, key.stop
    
    
def _get_dim(key, count):

    if isinstance(key, int):
        return ()
    else:
        return (count,)
