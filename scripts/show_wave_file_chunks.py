"""
Script that parses WAVE files chunk by chunk and prints information
about the chunks.
"""


import argparse
import os

from vesper.util.wave_file_utils import WaveFileFormatError
import vesper.util.wave_file_utils as wave_file_utils


def main():

    args = parse_args()

    for file_path in args.file_paths:

        try:
            show_wave_file_chunks(file_path)
        except WaveFileFormatError as e:
            print(f'WARNING: Could not parse file "{file_path}". {str(e)}')


def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            'Parse WAVE files chunk by chunk and print information '
            'about the chunks.'))

    parser.add_argument(
        'file_paths', metavar='file_path', type=str, nargs='+')

    return parser.parse_args()


def show_wave_file_chunks(file_path):

    print(f'File "{file_path}":')

    file_size = get_file_size(file_path)
    print(f'    file size (bytes): {file_size}')

    with open(file_path, 'rb') as f:

        print('    chunks:')

        riff_chunk = wave_file_utils.parse_riff_chunk_header(f)
        wave_file_utils.show_basic_chunk_info(riff_chunk)
        
        offset = 12

        while offset != file_size:

            chunk = wave_file_utils.parse_subchunk(f, offset)

            wave_file_utils.show_subchunk_info(chunk)

            offset += chunk.size + 8

    print()


def get_file_size(f):
    info = os.stat(f)
    return info.st_size


if __name__ == '__main__':
    main()
