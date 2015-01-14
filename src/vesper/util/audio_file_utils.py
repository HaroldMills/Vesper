"""Functions pertaining to audio files."""


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


def read_wave_file(path):
    
    # TODO: Handle file I/O errors.
    
    file_ = wave.open(path, 'rb')
    
    (num_channels, sample_size, frame_rate, num_frames,
     compression_type, _) = _call(file_, file_.getparams)
        
    _check_wave_file_format(sample_size, compression_type, path)
    
    frame_rate = float(frame_rate)
     
    string = _call(file_, file_.readframes, num_frames)
    samples = np.fromstring(string, dtype=_WAVE_SAMPLE_DTYPE)
    samples = samples.reshape((num_frames, num_channels)).transpose()
        
    file_.close()
    
    return (samples, frame_rate)


def _call(file_, method, *args, **kwds):
    try:
        return method(*args, **kwds)
    except:
        file_.close()
        raise


def _check_wave_file_format(sample_size, compression_type, path):
    
    if sample_size != 2:
        
        if sample_size == 1:
            s = 'one byte'
        else:
            s = '{} bytes'.format(sample_size)
            
        raise UnsupportedAudioFileFormatError(
            ('Wave file "{}" has unsupported sample size of {} bytes. Only '
             'two-byte samples are currently supported.').format(path, s))
        
    if compression_type != 'NONE':
        raise UnsupportedAudioFileFormatError(
            ('Wave file "{}" compression type is not "NONE". Only '
             'uncompressed audio files are currently supported.').format(path))


def write_wave_file(path, samples, frame_rate):
    
    # TODO: Handle file I/O errors.
    
    file_ = wave.open(path, 'wb')
        
    num_channels = samples.shape[0]
    sample_size = 2
    num_frames = 0
    compression_type = 'NONE'
    compression_name = 'not compressed'
    params = (num_channels, sample_size, frame_rate, num_frames,
              compression_type, compression_name)
    _call(file_, file_.setparams, params)
    
    # Get samples as one-dimensional array.
    if num_channels == 1:
        samples = samples[0]
    else:
        samples = samples.transpose().reshape(-1)
        
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(samples, dtype=_WAVE_SAMPLE_DTYPE)
        
    _call(file_, file_.writeframes, samples.tostring())
    
    file_.close()
