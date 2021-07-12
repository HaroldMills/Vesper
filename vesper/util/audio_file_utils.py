"""
Functions pertaining to audio files.

For the time being, this module supports only one-channel and two-channel
16-bit WAVE files. It includes support for incremental writes that open a
file, append samples to it, and close it. Python's `wave` module does not
seem to support incremental writes, which is desirable for recording.

It would be good to add support for reading and writing a wide variety of
audio files via a library like PySoundFile, even if we don't support
incremental writes for all formats. It would also be good to be able to
write 24-bit and 32-bit WAVE files, multichannel WAVE files, AIFF files,
and perhaps FLAC files incrementally.
"""


import io
import numpy as np
import wave

from vesper.util.bunch import Bunch
from vesper.util.byte_buffer import ByteBuffer


WAVE_FILE_NAME_EXTENSION = '.wav'
_WAVE_HEADER_SIZE = 44
_WAVE_FMT_CHUNK_SIZE = 24
_WAVE_RIFF_CHUNK_SIZE_OFFSET = 4
_WAVE_CHANNEL_COUNT_OFFSET = 22
_WAVE_BYTES_PER_SAMPLE_FRAME_OFFSET = 32
_WAVE_DATA_CHUNK_SIZE_OFFSET = 40
_WAVE_FORMAT_PCM = 0x0001
_WAVE_SAMPLE_DTYPE = np.dtype('<i2')


class AudioFileFormatError(Exception):
    pass


class UnsupportedAudioFileFormatError(AudioFileFormatError):
    pass


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
    
    dim_count = len(samples.shape)
    
    if dim_count != 1 and dim_count != 2:
        raise ValueError('Sample array must have one or two dimensions.')
    
    if dim_count == 1:
        # `samples` is one-dimensional
        
        # Assume file should have one channel.
        samples = samples.reshape((1, -1))
        
    # At this point `samples` is two-dimensional, with the first dimension
    # one or two, the channel count.
        
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
    
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(np.round(samples), dtype=_WAVE_SAMPLE_DTYPE)
        
    # Convert samples to bytes, interleaving samples of multiple channels.
    samples = samples.tobytes('F')
    
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


def write_empty_wave_file(file_path, channel_count, sample_rate, sample_size):
    
    """
    Writes a WAVE file containing zero samples.
    
    We currently support only mono and stereo WAVE files with 16-bit
    samples. Note that supporting larger numbers of channels and other
    sample sizes is not trivial. See the Microsoft documents that
    define the RIFF file format for details. These documents include:
    
        Multimedia Programming Interface and Data Specifications
        Version 1.0, 1991
        
        New Multimedia Data Types and Data Techniques
        Revision 3.0, 1994
        
        Multiple Channel Audio Data and WAVE Files
        2002
        
    As of this writing (2020-03-26), all of the above documents are
    available via the web site
    http://www-mmsp.ece.mcgill.ca/Documents/AudioFormats/WAVE/WAVE.html.
    """
    
    if channel_count != 1 and channel_count != 2:
        raise ValueError(
            'Sorry, but currently only mono and stereo WAVE files '
            'are supported.')
    
    if sample_size != 16:
        raise ValueError(
            'Sorry, but currently only 16-bit WAVE files are supported.')
    
    contents = _create_wave_file_header(
        channel_count, sample_rate, sample_size, 0)
    
    with open(file_path, 'wb') as file_:
        file_.write(contents)
    
    
def _create_wave_file_header(
        channel_count, sample_rate, sample_size, frame_count):
    
    bytes_per_sample_frame = channel_count * sample_size // 8
    byte_rate = sample_rate * bytes_per_sample_frame
    data_size = frame_count * bytes_per_sample_frame
    file_size = _WAVE_HEADER_SIZE + data_size
    
    b = ByteBuffer(_WAVE_HEADER_SIZE)
    
    b.write_bytes(b'RIFF')
    b.write_value(file_size - 8, '<I')
    b.write_bytes(b'WAVE')
    
    b.write_bytes(b'fmt ')
    b.write_value(_WAVE_FMT_CHUNK_SIZE - 8, '<I')
    b.write_value(_WAVE_FORMAT_PCM, '<H')
    b.write_value(channel_count, '<H')
    b.write_value(sample_rate, '<I')
    b.write_value(byte_rate, '<I')
    b.write_value(bytes_per_sample_frame, '<H')
    b.write_value(sample_size, '<H')
    
    b.write_bytes(b'data')
    b.write_value(data_size, '<I')
    
    return b.bytes
    
    
def write_wave_file_samples(file_path, start_index, samples):
    
    with open(str(file_path), 'r+b') as file_:
        
        # Read WAVE file header into `ByteBuffer`.
        header = ByteBuffer(bytearray(file_.read(_WAVE_HEADER_SIZE)))
        
        channel_count = header.read_value('<H', _WAVE_CHANNEL_COUNT_OFFSET)
        
        _check_wave_file_sample_array(samples, channel_count)
        
        # Get file size in sample frames.
        data_size = header.read_value('<I', _WAVE_DATA_CHUNK_SIZE_OFFSET)
        bytes_per_sample_frame = \
            header.read_value('<H', _WAVE_BYTES_PER_SAMPLE_FRAME_OFFSET)
        file_size = data_size // bytes_per_sample_frame
        
        if file_size < start_index:
            # file contains fewer than `start_index` sample frames
            
            # Seek to end of file.
            file_.seek(0, io.SEEK_END)
            
            # Append zeros so file has `start_index` sample frames.
            padding_size = (start_index - file_size) * bytes_per_sample_frame
            _write_zeros(file_, padding_size)
            
        else:
            # file contains at least `start_index` sample frames
            
            padding_size = 0
            
            # Seek to start of sample frame number `start_index`.
            offset = _WAVE_HEADER_SIZE + start_index * bytes_per_sample_frame
            file_.seek(offset, io.SEEK_SET)
            
            # Write samples.
            _write_samples_to_file(file_, samples)
                
        _update_chunk_sizes(file_, header)


def _check_wave_file_sample_array(samples, channel_count):
    
    shape = samples.shape
    
    if len(shape) != 2:
        raise ValueError(
            'Sample array for WAVE file write must have two dimensions.')
        
    if shape[0] != channel_count:
        raise ValueError(
            f'Sample array for WAVE file write has data for {shape[0]} '
            f'channels but file has {channel_count} channels.')
        
        
_MAX_ZERO_BUFFER_SIZE = 2 ** 20


def _write_zeros(file_, size):
    
    remaining = size
    zeros = None
    
    while remaining != 0:
        
        write_size = min(remaining, _MAX_ZERO_BUFFER_SIZE)
        
        if zeros is None or len(zeros) != write_size:
            zeros = bytes(write_size)
            
        remaining -= file_.write(zeros)
        
        
def _write_samples_to_file(file_, samples):
    
    # Ensure that samples are of the correct type.
    if samples.dtype != _WAVE_SAMPLE_DTYPE:
        samples = np.array(np.round(samples), dtype=_WAVE_SAMPLE_DTYPE)
        
    # Convert samples to bytes, interleaving samples of multiple channels.
    samples = samples.tobytes('F')
    
    # Write samples to file.
    write_size = file_.write(samples)
    
    if write_size != len(samples):
        _handle_file_write_error(len(samples), write_size)
        
        
def _handle_file_write_error(requested_size, actual_size):
    raise IOError(
        f'WAVE file write failed: only {actual_size} of '
        f'{requested_size} bytes were written.')
    

def _update_chunk_sizes(file_, header):
    
    file_.seek(0, io.SEEK_END)
    file_size = file_.tell()
    header.write_value(file_size - 8, '<I', _WAVE_RIFF_CHUNK_SIZE_OFFSET)
    
    data_size = file_size - _WAVE_HEADER_SIZE
    header.write_value(data_size, '<I', _WAVE_DATA_CHUNK_SIZE_OFFSET)
    
    file_.seek(0, io.SEEK_SET)
    write_size = file_.write(header.bytes)
    
    if write_size != len(header.bytes):
        _handle_file_write_error(len(header.bytes), write_size)
