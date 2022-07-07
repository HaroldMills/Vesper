"""Module containing class `WaveFileReader`."""


import os.path
import wave

import numpy as np

from vesper.signal.audio_file_reader import AudioFileReader
from vesper.signal.unsupported_audio_file_error import \
    UnsupportedAudioFileError


_WAVE_FILE_EXTENSIONS = frozenset(['.wav', '.WAV'])
    

class WaveFileReader(AudioFileReader):
    

    @staticmethod
    def is_wave_file(file_path):
        extension = os.path.splitext(file_path)[1]
        return extension in _WAVE_FILE_EXTENSIONS


    def __init__(self, file_, mono_1d=False):
        
        """
        Initializes this file reader for the specified file.
        
        `file_` may be either a string or a file-like object. If it is a
        string it should be the path of a WAVE file. If it is a file-like
        object, its contents should be a WAVE file.
        """
        
        
        if isinstance(file_, str):
            # `file_` is a file path
            
            file_path = file_
            
            if not os.path.exists(file_path):
                raise ValueError(f'File "{file_path}" does not exist.')
            
            if not WaveFileReader.is_wave_file(file_path):
                raise UnsupportedAudioFileError(
                    f'File "{file_path}" does not appear to be a WAVE file.')
                
            self._name = f'WAVE file "{file_path}"'
        
        else:
            # `file_` is a file-like object
            
            file_path = None
            self._name = 'WAVE file'
            
        try:
            self._reader = wave.open(file_, 'rb')
        except:
            raise OSError(f'Could not open {self._name}.')
        
        try:
            (channel_count, sample_width, sample_rate, length,
             compression_type, compression_name) = self._reader.getparams()
        except:
            self._reader.close()
            raise OSError(f'Could not read metadata from {self._name}.')
        
        sample_size = 8 * sample_width
        
        if compression_type != 'NONE':
            raise UnsupportedAudioFileError(
                f'{self._name} appears to contain compressed data (with '
                f'compression name "{compression_name}"), which is not '
                f'supported.')
            
        # TODO: support additional sample sizes, especially 24 bits.
        if sample_size != 8 and sample_size != 16:
            raise UnsupportedAudioFileError(
                f'{self._name} contains {sample_size}-bit samples, '
                f'which are not supported.')
            
        if sample_size == 8:
            dtype = np.uint8            # unsigned as per WAVE file spec
        else:
            dtype = np.dtype('<i2')
            
        super().__init__(
            file_path, channel_count, length, sample_rate, dtype, mono_1d)
        
        
    def read(self, start_index=0, length=None):
        
        if self._reader is None:
            raise OSError(f'Cannot read from closed {self._name}.')
        
        if start_index < 0 or start_index > self.length:
            raise ValueError(
                f'Read start index {start_index} is out of range '
                f'[0, {self.length}] for {self._name}.')
                             
        if length is None:
            # no length specified
            
            length = self.length - start_index
            
        else:
            # length specified
            
            stop_index = start_index + length
            
            if stop_index > self.length:
                # stop index exceeds file length
            
                raise ValueError(
                    f'Read stop index {stop_index} implied by start index '
                    f'{start_index} and read length {length} exceeds file '
                    f'length {self.length} for {self._name}.')
                        
        try:
            self._reader.setpos(start_index)
        except:
            self._reader.close()
            raise OSError(f'Set of read position failed for {self._name}.')

        try:
            buffer = self._reader.readframes(length)
        except:
            self._reader.close()
            raise OSError(f'Sample read failed for {self._name}.')
            
        samples = np.frombuffer(buffer, dtype=self.dtype)
        
        if len(samples) != length * self.channel_count:
            raise OSError(
                f'Got fewer samples than expected from read of {self._name}.')
        
        if self.channel_count == 1 and self.mono_1d:
            samples = samples.reshape((length,))
        else:
            samples = samples.reshape((length, self.channel_count)).transpose()
        
        # TODO: Deinterleave samples?
        # TODO: Byte swap samples on big endian platforms?
        
        return samples


    def close(self):
        if self._reader is not None:
            self._reader.close()
            self._reader = None
