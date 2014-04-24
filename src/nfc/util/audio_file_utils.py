"""Functions pertaining to audio files."""


import numpy as np
import wave


WAVE_FILE_NAME_EXTENSION = '.wav'


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
     compression_type, _) = file_.getparams()
        
    _check_wave_file_format(sample_size, compression_type, path)
    
    frame_rate = float(frame_rate)
     
    string = file_.readframes(num_frames)
    samples = np.fromstring(string, dtype='<i2')
    samples = samples.reshape((num_frames, num_channels)).transpose()
        
    file_.close()
    
    return (samples, frame_rate)


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
    file_.setparams(
        (num_channels, sample_size, frame_rate, num_frames,
         compression_type, compression_name))
    
    # TODO: Don't do these things if samples are already in the right form.
    samples = samples.transpose().reshape(-1)
    samples = np.array(samples, dtype='<i2')
    
    file_.writeframes(samples.tostring())
    
    file_.close()
