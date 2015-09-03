"""
Functions pertaining to audio files.

For the time being, only .wav files are supported.
"""


import numpy as np
import wave


WAVE_FILE_NAME_EXTENSION = '.wav'
_WAVE_SAMPLE_DTYPE = np.dtype('<i2')


class AudioFileFormatError(Exception):
    pass


class UnsupportedAudioFileFormatError(AudioFileFormatError):
    pass


def is_wave_file_path(path):
    return path.endswith(WAVE_FILE_NAME_EXTENSION)


# TODO: Either include compression name in return values or eliminate
# compression type. Consider implications of adding support for AIFF
# files to this module.
def get_wave_file_info(path):
    
    (file_, num_channels, sample_size, sample_rate, num_frames,
     compression_type, _) = _open_input_file(path, check_format=False)
    
    file_.close()
    
    return (num_channels, sample_size, sample_rate, num_frames,
            compression_type)
    
    
def _open_input_file(path, check_format=True):
    
    file_ = wave.open(path, 'rb')
    
    (num_channels, sample_size, sample_rate, num_frames, compression_type,
     compression_name) = _call(file_, file_.getparams)
        
    sample_size *= 8

    if check_format:
        _check_wave_file_format(sample_size, compression_type)
    
    sample_rate = float(sample_rate)
    
    return (file_, num_channels, sample_size, sample_rate, num_frames,
            compression_type, compression_name)
    
        
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
    
    # TODO: Handle file I/O errors.
    
    file_, num_channels, _, sample_rate, num_frames, _, _ = \
        _open_input_file(path)

    samples = _read_samples(file_, num_frames, num_channels)
    
    file_.close()
    
    return (samples, sample_rate)
    
    
def _read_samples(file_, num_frames, num_channels):
    string = _call(file_, file_.readframes, num_frames)
    samples = np.frombuffer(string, dtype=_WAVE_SAMPLE_DTYPE)
    samples = samples.reshape((num_frames, num_channels)).transpose()
    return samples
        

def _call(file_, method, *args, **kwds):
    try:
        return method(*args, **kwds)
    except:
        file_.close()
        raise


def write_wave_file(path, samples, sample_rate):
    # TODO: Handle file I/O errors.
    num_channels = samples.shape[0]
    file_ = _open_output_file(path, num_channels, sample_rate)    
    _write_samples(file_, samples)
    file_.close()


def _open_output_file(path, num_channels, sample_rate):
    
    file_ = wave.open(path, 'wb')
        
    sample_size = 2
    sample_rate = int(round(sample_rate))
    num_frames = 0
    compression_type = 'NONE'
    compression_name = 'not compressed'
    params = (num_channels, sample_size, sample_rate, num_frames,
              compression_type, compression_name)
    _call(file_, file_.setparams, params)
    
    return file_


def _write_samples(file_, samples):
    
    num_channels = samples.shape[0]
    
    # Get samples as one-dimensional array.
    if num_channels == 1:
        samples = samples[0]
    else:
        samples = samples.transpose().reshape(-1)
        
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(samples, dtype=_WAVE_SAMPLE_DTYPE)
        
    # Write samples.
    _call(file_, file_.writeframes, samples.tostring())
    

_DEFAULT_CHUNK_SIZE = 1000000


def copy_wave_file_channel(
        input_file_path, channel_num, output_file_path,
        chunk_size=_DEFAULT_CHUNK_SIZE):
    
    """Copies one channel of an existing audio file to a new audio file."""
    
    
    input_file, num_channels, _, sample_rate, num_frames, _, _ = \
        _open_input_file(input_file_path)
        
    try:
        
        output_file = _open_output_file(output_file_path, 1, sample_rate)
            
        try:
            
            remaining = num_frames
            
            while remaining != 0:
                
                n = min(remaining, chunk_size)
                
                samples = _read_samples(input_file, n, num_channels)
                channel_samples = samples[channel_num]
                _write_samples(output_file, channel_samples)
                
                remaining -= n
                
        finally:
            output_file.close()
            
    finally:
        input_file.close()

    