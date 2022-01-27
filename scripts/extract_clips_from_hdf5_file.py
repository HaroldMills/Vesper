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

            samples, attributes = read_clip(clip_group, clip_id)

            show_clip(clip_id, samples, attributes)

            write_wave_file(clip_id, samples, attributes['sample_rate'])


def read_clip(clip_group, clip_id):
    clip = clip_group[clip_id]
    samples = clip[:]
    attributes = dict((name, value) for name, value in clip.attrs.items())
    return samples, attributes


def show_clip(clip_id, samples, attributes):
    print(f'clip {clip_id}:')
    print(f'    length: {len(samples)}')
    print('    attributes:')
    for key in sorted(attributes.keys()):
        value = attributes[key]
        print(f'        {key}: {value}')
    print()
        

def write_wave_file(i, samples, sample_rate):
    file_name = f'{i}.wav'
    file_path = DIR_PATH / file_name
    with wave.open(str(file_path), 'wb') as file_:
        file_.setparams((1, 2, sample_rate, len(samples), 'NONE', ''))
        file_.writeframes(samples.tobytes())


if __name__ == '__main__':
    main()
