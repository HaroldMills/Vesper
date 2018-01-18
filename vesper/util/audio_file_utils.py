"""
Functions pertaining to audio files.

For the time being, only .wav files are supported.
"""


from pathlib import Path
import numpy as np
import wave

from vesper.util.bunch import Bunch


WAVE_FILE_NAME_EXTENSION = '.wav'
_WAVE_SAMPLE_DTYPE = np.dtype('<i2')


class AudioFileFormatError(Exception):
    pass


class UnsupportedAudioFileFormatError(AudioFileFormatError):
    pass


def is_wave_file_path(path):
    
    if isinstance(path, Path):
        return path.suffix == WAVE_FILE_NAME_EXTENSION
    
    elif isinstance(path, str):
        return path.endswith(WAVE_FILE_NAME_EXTENSION)
    
    else:
        raise TypeError(
            'Bad type "{}" for file path.'.format(
                path.__class__.__name__))


def get_wave_file_info(path):
    with wave.open(path, 'rb') as reader:
        return _read_header(reader, check_format=False)


def _read_header(reader, check_format=True):
    
    p = reader.getparams()
        
    sample_size = p.sampwidth * 8

    if check_format:
        _check_wave_file_format(sample_size, p.comptype)
    
    sample_rate = float(p.framerate)
    
    return Bunch(
        num_channels=p.nchannels,
        length=p.nframes,
        sample_size=sample_size,
        sample_rate=sample_rate,
        compression_type=p.comptype,
        compression_name=p.compname)
 
 
def _check_wave_file_format(sample_size, compression_type):
    
    if sample_size != 16:
        raise UnsupportedAudioFileFormatError(
            ('Audio file has unsupported sample size of {} bits. Only '
             '16-bit samples are currently supported.').format(sample_size))
        
    if compression_type != 'NONE':
        raise UnsupportedAudioFileFormatError(
            'Audio file compression type is not "NONE". Only uncompressed '
            'audio files are currently supported.')


def read_wave_file(path):
    
    with wave.open(path, 'rb') as reader:
        info = _read_header(reader)
        samples = _read_samples(reader, info.length, info.num_channels)
    
    return (samples, info.sample_rate)
    
    
def _read_samples(reader, length, num_channels):
    string = reader.readframes(length)
    samples = np.frombuffer(string, dtype=_WAVE_SAMPLE_DTYPE)
    if num_channels == 1:
        samples = samples.reshape((num_channels, length))
    else:
        samples = samples.reshape((length, num_channels)).transpose()
    return samples


def write_wave_file(path, samples, sample_rate):
    num_channels = samples.shape[0]
    with wave.open(path, 'wb') as writer:
        _write_header(writer, num_channels, sample_rate)
        _write_samples(writer, samples)
        
        
def _write_header(writer, num_channels, sample_rate):
    
    sample_size = 2
    sample_rate = int(round(sample_rate))
    length = 0
    compression_type = 'NONE'
    compression_name = 'not compressed'
    
    writer.setparams((
        num_channels, sample_size, sample_rate, length,
        compression_type, compression_name))
    
    
def _write_samples(writer, samples):
    
    num_channels = samples.shape[0]
    
    # Get samples as one-dimensional array.
    if num_channels == 1:
        samples = samples[0]
    else:
        samples = samples.transpose().reshape(-1)
        
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(samples, dtype=_WAVE_SAMPLE_DTYPE)
        
    # Convert samples to string.
    samples = samples.tostring()
    
    # Write to file.
    # This appears to slow down by about an order of magnitude after
    # we archive perhaps a gigabyte of data across hundreds of clips.
    # Not sure why. The slowdown also happens if we open regular files
    # instead of wave files and write samples to them with plain old
    # file_.write(samples).
    # TODO: Write simple test script that writes hundreds of files
    # containing zeros (a million 16-bit integers apiece, say) and
    # see if it is similarly slow. If so, is it slow on Mac OS X?
    # Is it slow on a non-parallels version of Windows? Is it slow
    # if we write the program in C instead of in Python?
    writer.writeframes(samples)


_DEFAULT_CHUNK_SIZE = 1000000


def copy_wave_file_channel(
        input_file_path, channel_num, output_file_path,
        chunk_size=_DEFAULT_CHUNK_SIZE):
    
    """Copies one channel of an existing audio file to a new audio file."""
    
    
    with wave.open(input_file_path, 'rb') as reader:
        
        info = _read_header(reader)
        
        with wave.open(output_file_path, 'wb') as writer:
            
            _write_header(writer, 1, info.sample_rate)
            
            remaining = info.length
            
            while remaining != 0:
                
                n = min(remaining, chunk_size)
                
                samples = _read_samples(reader, n, info.num_channels)
                channel_samples = samples[channel_num]
                _write_samples(writer, channel_samples)
                
                remaining -= n
