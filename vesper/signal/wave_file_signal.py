"""Module containing class `WaveFileSignal`."""


from pathlib import Path
import wave

import numpy as np

from vesper.signal.audio_file_signal import AudioFileSignal
from vesper.signal.sample_provider import SampleProvider
from vesper.signal.signal_error import SignalError


class WaveFileSignal(AudioFileSignal):
    
    
    def __init__(self, file, name=None):
        
        # Get `file` as `Path` if possible.
        file_path = _get_file_path(file)
            
        # `file` can be a `Path`, a `str`, or a file-like object. If it
        # is a `Path`, convert it to a `str` so we can call `wave.open`
        # with it (as of Python 3.8, `wave.open` accepts either a `str`
        # or a file-like argument, but not a `Path`).
        if isinstance(file, Path):
            file = str(file)
        else:
            file = file
            
        with wave.open(file, mode='rb') as reader:
            
            frame_count = reader.getnframes()
            frame_rate = reader.getframerate()
            channel_count = reader.getnchannels()
            
            sample_size = 8 * reader.getsampwidth()
            if sample_size != 16:
                _raise_signal_error(
                    f'Unsupported sample size of {sample_size} bits',
                    file_path)
            else:
                dtype = np.dtype('<i2')
 
            if reader.getcomptype() != 'NONE':
                _raise_signal_error((
                    f'Unsupported compression type of '
                    f'"{reader.getcompname()}"'), file_path)
                
        file_format = _get_file_format(channel_count, sample_size, frame_rate)
        
        sample_provider = _SampleProvider(file, channel_count, dtype)
        
        super().__init__(
            frame_count, frame_rate, channel_count, dtype, sample_provider,
            name, file_path, file_format)
        

def _get_file_path(file):
    
    if isinstance(file, Path):
        return file
    elif isinstance(file, str):
        return Path(file)
    else:
        return None


def _raise_signal_error(prefix, file_path):
    
    if file_path is None:
        path = ''
    else:
        path = f' "{file_path}"'
        
    message = f'{prefix} for WAVE audio file{path}.'
    
    raise SignalError(message)
    
        
def _get_file_format(channel_count, sample_size, frame_rate):
    
    if channel_count == 1:
        channel_string = 'Mono'
    elif channel_count == 2:
        channel_string = 'Stereo'
    else:
        channel_string = f'{channel_count}-channel'
        
    return f'{channel_string}, {sample_size}-bit, {frame_rate} Hz WAVE'
       
       
class _SampleProvider(SampleProvider):
    
    
    def __init__(self, file, channel_count, dtype):
        
        super().__init__(True)
        
        self._file = file
        self._channel_count = channel_count
        self._dtype = dtype
        
        self._file_path = _get_file_path(file)

        with wave.open(self._file, mode='rb') as reader:
            self._frame_count = reader.getnframes()
            self._channel_count = reader.getnchannels()
        
        
    def get_samples(self, frame_key, channel_key):
        
        start_frame, end_frame = _get_bounds(frame_key)
        frame_count = end_frame - start_frame
        
        start_channel, end_channel = _get_bounds(channel_key)
        channel_count = end_channel - start_channel
        
        with wave.open(self._file, mode='rb') as reader:
            
            # Set read position.
            try:
                reader.setpos(start_frame)
            except Exception:
                _raise_signal_error(
                    'Set of read position failed', self._file_path)
    
            # Read sample data.
            try:
                buffer = reader.readframes(frame_count)
            except Exception:
                _raise_signal_error('Samples read failed', self._file_path)
                
        # Check actual read size.
        byte_count = frame_count * self._channel_count * self._dtype.itemsize
        if len(buffer) != byte_count:
            _raise_signal_error(
                f'Read {len(buffer)} bytes rather than expected {byte_count}',
                self._file_path)
            
        # Convert sample data to one-dimensional NumPy array.
        samples = np.frombuffer(buffer, dtype=self._dtype)
        
        # Reshape sample array to two dimensions.
        samples.shape = (frame_count, self._channel_count)
        
        # Select channels if needed.
        if start_channel != 0 or end_channel != self._channel_count:
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
    return (count,) if isinstance(key, slice) else ()
