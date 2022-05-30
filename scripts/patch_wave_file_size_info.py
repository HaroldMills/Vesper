"""
Script that patches WAVE files that indicate that they contain zero
sample frames but do not.

More than one Vesper user has wound up with such files from third-party
recording software, including at least i-Sound Recorder.

The script assumes that the files it is given are valid WAVE audio
files containing PCM sample data, except that the RIFF and data
chunk sizes are zero, and also the fact chunk frame count if the
fact chunk is present. It also assumes that the data chunk is the
final chunk of the file.

The script deduces the size of the data chunk from its offset in
the file and the file size, and writes correct size data to the
RIFF, fact (if present), and data chunks.
"""


import argparse
import os
import struct

import vesper.util.wave_file_utils as wave_file_utils


def main():

    args = parse_args()

    for file_path in args.file_paths:

        try:
            patch_wave_file_size_info(file_path, args.dry_run, args.verbose)
        except Exception as e:
            print(f'WARNING: Did not patch file "{file_path}": {str(e)}')


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            'Patch WAVE files that indicate that they contain zero '
            'sample frames but do not.'))

    parser.add_argument(
        '-d', '--dry-run', action='store_true', default=False,
        help="print output but don't actually modify any files")

    parser.add_argument(
        '-v', '--verbose', action='store_true', default=False,
        help="print extra output")

    parser.add_argument(
        'file_paths', metavar='file_path', type=str, nargs='+')

    return parser.parse_args()


def patch_wave_file_size_info(file_path, dry_run, verbose):

    print(f'Processing file "{file_path}"...')

    file_size = get_file_size(file_path)

    riff_chunk, fmt_chunk, fact_chunk, data_chunk = \
        parse_file(file_path, file_size)

    if verbose:
        print(f'    file size (bytes): {file_size}')
        print(f'    chunks:')
        show_chunk = wave_file_utils.show_basic_chunk_info
        show_chunk(riff_chunk)
        show_chunk(fmt_chunk)
        show_chunk(fact_chunk)
        show_chunk(data_chunk)

    if riff_chunk.size != 0:
        raise _Error('RIFF chunk size in file is not zero.')

    if fact_chunk is not None and fact_chunk.frame_count != 0:
        raise _Error('fact chunk frame count in file is not zero.')

    if data_chunk.size != 0:
        raise _Error('data chunk size in file is not zero.')

    riff_chunk_size = file_size - 8

    sample_data_start_offset = data_chunk.offset + 8
    data_chunk_size = file_size - sample_data_start_offset
    frame_size = fmt_chunk.block_size

    if data_chunk_size % frame_size != 0:
        raise _Error(
            f'Frame size {frame_size} does not divide data chunk size '
            f'{data_chunk_size}.')

    frame_count = data_chunk_size // frame_size

    if verbose:
        print(f'    correct RIFF chunk size: {riff_chunk_size}')
        print(f'    correct frame count: {frame_count}')
        print(f'    correct data chunk size: {data_chunk_size}')

    if not dry_run:

        if verbose:
            print('    correcting size info...')

        with open(file_path, 'r+b') as f:

            # Write correct RIFF chunk size.
            write_u4(f, riff_chunk_size, riff_chunk.offset + 4)

            # Write correct frame count to fact chunk if present.
            if fact_chunk is not None:
                write_u4(f, frame_count, fact_chunk.offset + 8)

            # Write correct data chunk size.
            write_u4(f, data_chunk_size, data_chunk.offset + 4)


def write_u4(f, value, offset):
    data = struct.pack('<I', value)
    f.seek(offset)
    f.write(data)


def parse_file(file_path, file_size):

    with open(file_path, 'rb') as f:

        riff_chunk = wave_file_utils.parse_riff_chunk_header(f)
        fmt_chunk = None
        fact_chunk = None
        data_chunk = None
        
        offset = 12

        while offset != file_size:

            chunk = wave_file_utils.parse_subchunk(f, offset)

            if chunk.id == wave_file_utils.FMT_CHUNK_ID:
                fmt_chunk = chunk
            elif chunk.id == wave_file_utils.FACT_CHUNK_ID:
                fact_chunk = chunk
            elif chunk.id == wave_file_utils.DATA_CHUNK_ID:
                data_chunk = chunk
                break

            offset += chunk.size + 8

    return riff_chunk, fmt_chunk, fact_chunk, data_chunk


def get_file_size(f):
    info = os.stat(f)
    return info.st_size


class _Error(Exception):
    pass


if __name__ == '__main__':
    main()
