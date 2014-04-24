"""Functions that create and load NFC classification datasets."""


from __future__ import print_function

from collections import defaultdict
import itertools
import os.path
import random

import numpy as np

from nfc.archive.archive import Archive


_CSV_FILE_NAME = 'clips.csv'


def create_clip_dataset(
    archive_dir_path, dataset_dir_path, dataset_size, clip_class_names,
    clip_class_fractions=None):
    
    # TODO: Balance counts from different stations.
    # TODO: Filter by station and date.
    # TODO: Raise an exception if dataset directory does not exist or
    #       is not empty.
    
    if clip_class_fractions is None:
        n = len(clip_class_names)
        clip_class_fractions = np.ones(n) / n
        
    counts = np.array(np.round(clip_class_fractions * dataset_size),
                      dtype='int')
    
    archive = Archive.open(archive_dir_path)
    file_name_lists = []
    
    for name, count in zip(clip_class_names, counts):
        
        print('getting clips of class "{:s}"...'.format(name))
        clips = _get_clips(archive, name, count)
    
        print('creating clip files for class "{:s}"...'.format(name))
        file_names = _create_clip_files(clips, dataset_dir_path)
        
        file_name_lists.append(file_names)
    
    print('creating csv file...')
    _create_csv_file(file_name_lists, dataset_dir_path)
    
    
def _create_csv_file(file_name_lists, dataset_dir_path):
    
    line_lists = [_create_csv_line_list(l, i)
                 for i, l in enumerate(file_name_lists)]
    
    lines = list(itertools.chain(*line_lists))
    lines.sort()
    
    file_path = os.path.join(dataset_dir_path, _CSV_FILE_NAME)
    with open(file_path, 'w') as file_:
        file_.writelines(lines)
    
    
def _create_csv_line_list(file_names, class_num):
    class_num = ',' + str(class_num) + '\n'
    return [name + class_num for name in file_names]


def _get_clips(archive, clip_class_name, num_clips):
    
    clips = archive.get_clips(clip_class_name=clip_class_name)
    
    # TODO: Issue a warning here rather than raising an exception?
    if num_clips > len(clips):
        raise ValueError(
            ('Cannot create dataset with {:d} "{:s}" clips, since archive '
             'contains only {:d}.').format(
                 num_clips, clip_class_name, len(clips)))
        
    _show_station_counts(clips)
    
    return random.sample(clips, num_clips)


def _show_station_counts(clips):
    counts = defaultdict(int)
    for clip in clips:
        counts[clip.station_name] += 1
    keys = counts.keys()
    keys.sort()
    threshold = 0
    keys = [key for key in keys if counts[key] >= threshold]
    for i, key in enumerate(keys):
        print(i, key, counts[key])
    print()
        
        
def _create_clip_files(clips, dataset_dir_path):
    return [_create_clip_file(clip, dataset_dir_path) for clip in clips]


def _create_clip_file(clip, dataset_dir_path):
    file_name = _create_clip_file_name(
                    clip.station_name, clip.detector_name, clip.time)
#    file_path = os.path.join(dataset_dir_path, file_name)
    # TODO: Create the file.
    return file_name


_CLIP_FILE_NAME_EXTENSION = '.wav'


# TODO: This is redundant with function of same name in `Archive`. Fix this.
def _create_clip_file_name(station_name, detector_name, clip_time):
    millisecond = int(round(clip_time.microsecond / 1000.))
    time = clip_time.strftime('%Y-%m-%d_%H.%M.%S') + \
           '.{:03d}'.format(millisecond)
    return '{:s}_{:s}_{:s}{:s}'.format(
               station_name, detector_name, time, _CLIP_FILE_NAME_EXTENSION)


def load_dataset(dir_path):
    pass
