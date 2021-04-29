"""Module containing class `WaveAudioFileType`."""


import os.path
import wave

import numpy as np

from vesper.signal.audio_file_reader import AudioFileReader
from vesper.signal.unsupported_audio_file_error import UnsupportedAudioFileError


'''
audio_file_utils:
    read_audio_file(file_path)
    write_audio_file(file_path, waveform)
    
    
class AudioFileType:
    name
    reader_class
    writer_class
    is_recognized_file(file_path)
    
    
class AudioFileReader:

    file_type
    
    num_channels
    length
    sample_rate
    dtype

    read(start_index=0, length=None, samples=None)

    close()


class AudioFileWriter:

    file_type
    
    num_channels
    length
    sample_rate
    dtype
    
    append(samples)
    
    close()
    
    
class WaveFileReader(AudioFileReader):
    __init__(file_path)
    

class WaveFileWriter(AudioFileWriter):
     __init__(file_path, num_channels, sample_rate, dtype=None)
'''


class WaveAudioFileReader(AudioFileReader):
    

    def __init__(self, file_, mono_1d=False):
        
        """
        Initializes this file reader for the specified file.
        
        `file_` may be either a string or a file-like object. If it is a
        string it should be the path of a WAV file. If it is a file-like
        object, its contents should be a WAV file.
        """
        
        
        if isinstance(file_, str):
            # `file_` is a file path
            
            file_path = file_
            
            if not os.path.exists(file_path):
                raise ValueError('File "{}" does not exist.'.format(file_path))
            
            if not WaveAudioFileType.is_supported_file(file_path):
                raise UnsupportedAudioFileError(
                    'File "{}" does not appear to be a WAV file.'.format(
                        file_path))
                
            self._name = 'WAV file "{}"'.format(file_path)
        
        else:
            # `file_` is a file-like object
            
            file_path = None
            self._name = 'WAV file'
            
        try:
            self._reader = wave.open(file_, 'rb')
        except:
            raise OSError('Could not open {}.'.format(self._name))
        
        try:
            (num_channels, sample_width, sample_rate, length, compression_type,
             compression_name) = self._reader.getparams()
        except:
            self._reader.close()
            raise OSError('Could not read metadata from {}.'.format(self._name))
        
        sample_size = 8 * sample_width
        
        if compression_type != 'NONE':
            raise UnsupportedAudioFileError((
                '{} appears to contain compressed data (with '
                'compression name "{}"), which is not '
                'supported.').format(self._name, compression_name))
            
        # TODO: support additional sample sizes, especially 24 bits.
        if sample_size != 8 and sample_size != 16:
            raise UnsupportedAudioFileError((
                '{} contains {}-bit samples, which are '
                'not supported.').format(self._name, sample_size))
            
        if sample_size == 8:
            dtype = np.uint8            # unsigned as per WAVE file spec
        else:
            dtype = np.dtype('<i2')
            
        super().__init__(
            file_path, WaveAudioFileType, num_channels, length, sample_rate,
            dtype, mono_1d)
        
        
    def read(self, start_index=0, length=None):
        
        if self._reader is None:
            raise OSError('Cannot read from closed {}.'.format(self._name))
        
        if start_index < 0 or start_index > self.length:
            raise ValueError((
                'Read start index {} is out of range [{}, {}] for '
                '{}.').format(start_index, 0, self.length, self._name))
                             
        if length is None:
            # no length specified
            
            length = self.length - start_index
            
        else:
            # length specified
            
            stop_index = start_index + length
            
            if stop_index > self.length:
                # stop index exceeds file length
            
                raise ValueError((
                    'Read stop index {} implied by start index {} and read '
                    'length {} exceeds file length {} for {}.').format(
                        stop_index, start_index, length, self.length,
                        self._name))
                        
        try:
            self._reader.setpos(start_index)
        except:
            self._reader.close()
            raise OSError(
                'Set of read position failed for {}.'.format(self._name))

        try:
            buffer = self._reader.readframes(length)
        except:
            self._reader.close()
            raise OSError('Samples read failed for {}.'.format(self._name))
            
        samples = np.frombuffer(buffer, dtype=self.dtype)
        
        if len(samples) != length * self.num_channels:
            raise OSError(
                'Got fewer samples than expected from read of {}.'.format(
                    self._name))
        
        if self.num_channels == 1 and self.mono_1d:
            samples = samples.reshape((length,))
        else:
            samples = samples.reshape((length, self.num_channels)).transpose()
        
        # TODO: Deinterleave samples?
        # TODO: Byte swap samples on big endian platforms?
        
        return samples


    def close(self):
        if self._reader is not None:
            self._reader.close()
            self._reader = None


class WaveAudioFileType:
    

    name = 'WAV Audio File Type'
    
    reader_class = WaveAudioFileReader
    
    # writer_class = WaveAudioFileWriter
    
    file_name_extensions = frozenset(['.wav', '.WAV'])
    
    @staticmethod
    def is_supported_file(file_path):
        extension = os.path.splitext(file_path)[1]
        return extension in WaveAudioFileType.file_name_extensions
