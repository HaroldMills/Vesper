from pathlib import Path
import random
import time

import soundfile as sf


DIR_PATH = Path('/Users/harold/Desktop/NFC/FLAC Test')
# DIR_PATH = Path('/Volumes/Recordings1/FLAC Test')
FILE_NAME_STEM = 'FLOOD-21C_20180901_194500'

CLIP_COUNT = 10000
CLIP_DURATION = .6
SAMPLE_RATE = 24000
CLIP_LENGTH = int(round(CLIP_DURATION * SAMPLE_RATE))


def main():
    start_indices = generate_clip_start_indices()
    read_clips(start_indices, 'flac')
    read_clips(start_indices, 'wav')


def read_clips(start_indices, extension):

    file_path = get_file_path(extension)

    with sf.SoundFile(file_path) as file_:

        start_time = time.time()

        for start_index in start_indices:
            samples = read(file_, start_index, CLIP_LENGTH)
            # print(samples[:10])

        delta_time = time.time() - start_time
        rate = CLIP_COUNT / delta_time
        print(
            f'Read {CLIP_COUNT} clips in {delta_time:.1f} seconds, '
            f'a rate of {rate:.1f} clips per second.')


def generate_clip_start_indices():

    file_path = get_file_path('wav')

    with sf.SoundFile(file_path) as file_:
        frame_count = file_.frames
        population = range(frame_count - CLIP_LENGTH)
        start_indices = random.choices(population, k=CLIP_COUNT)

    return start_indices


def get_file_path(extension):
    file_name = f'{FILE_NAME_STEM}.{extension}'
    return DIR_PATH / file_name


def read(file_, start_index, length):
    file_.seek(start_index)
    return file_.read(length, dtype='int16')


if __name__ == '__main__':
    main()
