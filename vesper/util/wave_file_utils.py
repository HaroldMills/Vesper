"""Utility functions, constants, and classes pertaining to WAVE audio files."""


import struct

from vesper.util.bunch import Bunch


class WaveFileFormatError(Exception):
    pass


RIFF_CHUNK_ID = 'RIFF'
FMT_CHUNK_ID = 'fmt '
FACT_CHUNK_ID = 'fact'
DATA_CHUNK_ID = 'data'

_WAVE_FORM_TYPE = 'WAVE'
_FMT_CHUNK_SIZES = (16, 18, 40)


def parse_riff_chunk_header(f):

    id = read_id(f, 0)
    if (id != RIFF_CHUNK_ID):
        raise WaveFileFormatError(
            'Purported WAVE audio file does not start with "RIFF".')

    size = read_u4(f, 4)

    form_type = read_id(f, 8)
    if (form_type != _WAVE_FORM_TYPE):
        raise WaveFileFormatError(
            f'Purported WAVE audio file does not have expected RIFF '
            f'form type "{_WAVE_FORM_TYPE}" in bytes 8-11.')

    return Bunch(id=RIFF_CHUNK_ID, offset=0, size=size)

        
def parse_subchunk(f, offset):

    id = read_id(f, offset)
    size = read_u4(f, offset + 4)

    chunk = Bunch(id=id, offset=offset, size=size)

    parser = _subchunk_parsers.get(id)

    if parser is not None:
        parser(f, offset, chunk)
    
    return chunk


def read_id(f, offset):
    f.seek(offset)
    data = f.read(4)
    return data.decode('UTF-8')


def read_u2(f, offset):
    f.seek(offset)
    data = f.read(2)
    return struct.unpack('<H', data)[0]


def read_u4(f, offset):
    f.seek(offset)
    data = f.read(4)
    return struct.unpack('<I', data)[0]


def parse_fact_chunk(f, offset, chunk):
    frame_count = read_u4(f, offset + 8)
    chunk.frame_count = frame_count


def parse_fmt_chunk(f, offset, chunk):

    if chunk.size not in _FMT_CHUNK_SIZES:

        raise WaveFileFormatError(
            f'WAVE audio file fmt chunk size is {chunk.size} bytes '
            f'rather than one of the expected {str(_FMT_CHUNK_SIZES)}. '
            f'Will only parse chunk header.')

    else:
        # chunk is of one of the expected sizes

        chunk.format_code = read_u2(f, offset + 8)
        chunk.channel_count = read_u2(f, offset + 10)
        chunk.sample_rate = read_u4(f, offset + 12)
        chunk.data_rate = read_u4(f, offset + 16)
        chunk.block_size = read_u2(f, offset + 20)
        chunk.sample_size = read_u2(f, offset + 22)

        if chunk.size > 16:
            chunk.extension_size = read_u2(f, offset + 24)


_subchunk_parsers = {
    FACT_CHUNK_ID: parse_fact_chunk,
    FMT_CHUNK_ID: parse_fmt_chunk,
 }


def show_subchunk_info(chunk):
    formatter = _subchunk_formatters.get(chunk.id)
    if formatter is None:
        show_basic_chunk_info(chunk)
    else:
        formatter(chunk)


def show_basic_chunk_info(chunk):
    print(f'        {chunk.id}')
    print(f'            chunk offset (bytes): {chunk.offset}')
    print(f'            chunk size (bytes): {chunk.size}')


def show_fact_chunk(chunk):
    show_basic_chunk_info(chunk)
    print(f'            frame count: {chunk.frame_count}')


def show_fmt_chunk(chunk):

    show_basic_chunk_info(chunk)

    if chunk.size in _FMT_CHUNK_SIZES:

        format = get_audio_data_format(chunk.format_code)
        print(f'            format: {format}')
        print(f'            channel count: {chunk.channel_count}')
        print(
            f'            sample rate (frames per second): '
            f'{chunk.sample_rate}')
        print(f'            data rate (bytes per second): {chunk.data_rate}')
        print(f'            block size (bytes): {chunk.block_size}')
        print(f'            sample size (bits): {chunk.sample_size}')

        if chunk.size > 16:
            print(
                f'            extension_size (bytes): {chunk.extension_size}')


_subchunk_formatters = {
    FACT_CHUNK_ID: show_fact_chunk,
    FMT_CHUNK_ID: show_fmt_chunk,
}


def get_audio_data_format(format_code):
    return audio_data_formats.get(
        format_code, 'Unrecognized (code {format_code})')


audio_data_formats = {
    0x0001: 'PCM',
    0x0003: 'IEEE Float',
    0x0006: 'A-law',
    0x0007: '\u03bc-law',
    0xFFFE: 'extensible',
}
