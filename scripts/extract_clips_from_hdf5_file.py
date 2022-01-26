from pathlib import Path
import wave

import h5py


DIR_PATH = Path('/Users/harold/Desktop/Clips')
INPUT_FILE_PATH = DIR_PATH / 'Clips.h5'
CLIP_COUNT = 5


def main():

    with h5py.File(INPUT_FILE_PATH, 'r') as file_:

        clip_group = file_['clips']

        for i, clip_id in enumerate(clip_group):

            if i == CLIP_COUNT:
                break

            samples, sample_rate = read_clip(clip_group, clip_id)

            print(clip_id, len(samples), samples.dtype, sample_rate)

            write_wave_file(clip_id, samples, sample_rate)


def read_clip(clip_group, clip_id):
    clip = clip_group[clip_id]
    samples = clip[:]
    sample_rate = clip.attrs['sample_rate']
    return samples, sample_rate


def write_wave_file(i, samples, sample_rate):
    file_name = f'{i}.wav'
    file_path = DIR_PATH / file_name
    with wave.open(str(file_path), 'wb') as file_:
        file_.setparams((1, 2, sample_rate, len(samples), 'NONE', ''))
        file_.writeframes(samples.tobytes())


if __name__ == '__main__':
    main()
