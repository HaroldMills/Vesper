from collections import defaultdict
from pathlib import Path
import itertools
import math
import os
import random
import time

import h5py
import resampy
import tensorflow as tf

import vesper.signal.resampling_utils as resampling_utils
import vesper.util.os_utils as os_utils


'''
The basic functions of this script are to:

   * Group related HDF5 files into *clip sets*.
   * For each clip set:
       * Filter clips (e.g. to exclude clips from certain station-nights).
       * Shuffle (i.e. randomly order) filtered clips.
       * Divide clips by sub-dataset (training, validation, etc.)
       * Write clips to tfrecord files.
   
The script does this in a storage-efficient way. It maintains in memory
an efficient representation of only one clip set at a time. The
representation includes only a minimal (HDF5 file ID, clip ID)
representation of each clip of the set. Some sort of representation of
each clip is needed for shuffling.

Different clip sets are combined (e.g. interleaved) using TensorFlow datasets.

Configuration:

    * HDF5 file groupings
    * Clip filters
    * Sub-dataset sizes
    * Max tfrecord file size in clips
    * Clip start offset, duration, and sample rate
    * Labeling (e.g. classification -> label map)
    
Classification dataset file name example:

    Tseep Classification 14k_Training_Call.ATSP_0000.tfrecords
'''


DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NOGO Coarse Classifier 0.0')

INPUT_DIR_PATH = DATA_DIR_PATH / 'HDF5 Files'

DATASET_SIZES = {
    'Training': .9,
    'Validation': .1
}

DATASET_SIZE_EPSILON = 1e-6

OUTPUT_DIR_PATH = DATA_DIR_PATH / 'Datasets'
OUTPUT_FILE_NAME_FORMAT = '{}_{}_{:04d}.tfrecords'
OUTPUT_FILE_SIZE = 10000  # examples

EXAMPLE_START_OFFSET = 0
"""Dataset example start offset, in seconds."""

EXAMPLE_DURATION = .6
"""Dataset example duration, in seconds."""

EXAMPLE_SAMPLE_RATE = 48000

CLASSIFICATION_LABELS = {
    'Other': 0,
    'NOGO': 1,
}
"""
Mapping from classification strings used in HDF5 files to numeric labels
used in datasets.
"""


def main():
    
    validate_config()
    
    input_file_path_lists = get_input_file_path_lists()
    
    delete_dir_if_exists(OUTPUT_DIR_PATH)
        
    for classification, input_file_paths in input_file_path_lists.items():
        write_output_files(classification, input_file_paths)
               
    
def validate_config():
    validate_dataset_sizes(DATASET_SIZES)
    
    
def validate_dataset_sizes(sizes):
    total = sum(sizes.values())
    if total - 1 >= DATASET_SIZE_EPSILON:
        raise ValueError(
            f'Dataset sizes sum to more than one. The sizes are: {sizes}.')
    
    
def get_input_file_path_lists():
    
    file_path_lists = defaultdict(list)
    file_paths = sorted(INPUT_DIR_PATH.glob('*.h5'))
    
    for path in file_paths:
        
        # Get classification from file path.
        classification = get_classification(path)
        
        file_path_lists[classification].append(path)
        
    return file_path_lists
    
    
def get_classification(file_name):
    return file_name.stem.split('_')[1]


def delete_dir_if_exists(dir_path):
    if os.path.exists(dir_path):
        os_utils.delete_directory(str(dir_path))


def write_output_files(classification, input_file_paths):
    
    # Read minimal clip representations from input files.
    clips = get_clips(input_file_paths)
    
    # Shuffle clips.
    random.shuffle(clips)
    
    # Partition clips by dataset.
    index_ranges = partition_clips(len(clips))
    
    for dataset_name, index_range in index_ranges.items():
        write_output_files_aux(
            classification, input_file_paths, clips, dataset_name, index_range)
    
    # show_clip_set_file_paths(classification, file_paths)
    
    
def get_clips(input_file_paths):
    clip_lists = [get_clips_aux(*p) for p in enumerate(input_file_paths)]
    return list(itertools.chain.from_iterable(clip_lists))
    
    
def get_clips_aux(file_num, file_path):
    with h5py.File(file_path, 'r') as file_:
        clip_group = file_['clips']
        return [(file_num, clip_id) for clip_id in clip_group]
        

def close_input_files(files):
    for f in files:
        f.file.close()
        
        
def partition_clips(total_clip_count):
    
    pairs = sorted(DATASET_SIZES.items())
    index_ranges = {}
    
    start_index = 0
    
    for dataset_name, fraction in pairs:
        
        clip_count = int(round(fraction * total_clip_count))
        
        end_index = start_index + clip_count
        index_ranges[dataset_name] = (start_index, end_index)
        
        start_index = end_index
        
    return index_ranges


def write_output_files_aux(
        classification, input_file_paths, clips, dataset_name, index_range):
    
    start_time = time.time()
    
    start_index, end_index = index_range
    clip_count = end_index - start_index
    file_count = int(math.ceil(clip_count / OUTPUT_FILE_SIZE))
    
    clip_num = 0
    file_num = 0
    
    while clip_num != clip_count:
        
        end_clip_num = min(clip_num + OUTPUT_FILE_SIZE, clip_count)
        output_file_clips = \
            clips[start_index + clip_num:start_index + end_clip_num]
        
        output_file_path = \
            get_output_file_path(dataset_name, classification, file_num)
        
        print(
            f'    Writing {len(output_file_clips)} clips to file '
            f'"{output_file_path}" (file {file_num + 1} of {file_count})...')
    
        write_output_file(
            input_file_paths, output_file_clips, output_file_path)
               
        clip_num = end_clip_num
        file_num += 1
        
    end_time = time.time()
    delta = end_time - start_time
    rate = clip_count / delta
    print(
        f'        Wrote {clip_count} {dataset_name} clips to {file_count} '
        f'files in {delta:.1f} seconds, a rate of {rate:.1f} clips per '
        f'second.')

    
def get_output_file_path(dataset_name, classification, file_num):
    
    file_name = OUTPUT_FILE_NAME_FORMAT.format(
        dataset_name, classification, file_num)
    
    return OUTPUT_DIR_PATH / dataset_name / file_name


def write_output_file(input_file_paths, output_file_clips, output_file_path):
    
    os_utils.create_parent_directory(output_file_path)
    
    with ClipGetter(input_file_paths) as clip_getter:
        
        with tf.io.TFRecordWriter(str(output_file_path)) as writer:
            
            for input_file_num, clip_id in output_file_clips:
                
                clip_ds = clip_getter.get_clip(input_file_num, clip_id)
                tf_example = create_tf_example(clip_ds)
                writer.write(tf_example.SerializeToString())
     

class ClipGetter:
    
    
    def __init__(self, input_file_paths):
        self._input_file_paths = input_file_paths
 
        
    def __enter__(self):
        self._input_files = {}
        self._clip_groups = {}
        return self
        
       
    def get_clip(self, input_file_num, clip_id):
        
        clip_group = self._clip_groups.get(input_file_num)
        
        if clip_group is None:
            
            file_path = self._input_file_paths[input_file_num]
            
            # print(f'        Opening file "{file_path}...')
            
            file_ = h5py.File(file_path, 'r')
            self._input_files[input_file_num] = file_
            
            clip_group = file_['clips']
            self._clip_groups[input_file_num] = clip_group
             
        return clip_group[clip_id]
    
    
    def __exit__(self, *_):
        
        for file_ in self._input_files.values():
            file_.close()

#         for file_num, file_ in sorted(self._input_files.items()):
#             
#             file_path = self._input_file_paths[file_num]
#             print(f'        Closing file "{file_path}...')
#             
#             file_.close()
            
            
def create_tf_example(clip_ds):
    
    waveform = clip_ds[:]
    attrs = clip_ds.attrs
    
    sample_rate = attrs['sample_rate']
    
    # Trim waveform.
    start_index = int(round(EXAMPLE_START_OFFSET * sample_rate))
    length = int(round(EXAMPLE_DURATION * sample_rate))
    waveform = waveform[start_index:start_index + length]
    
    # Resample waveform if needed.
    if sample_rate != EXAMPLE_SAMPLE_RATE:
        if EXAMPLE_SAMPLE_RATE == 24000:
            waveform = resampling_utils.resample_to_24000_hz(
                waveform, sample_rate)
        else:
            waveform = resampy.resample(
                waveform, sample_rate, EXAMPLE_SAMPLE_RATE)
    
    waveform_feature = create_bytes_feature(waveform.tobytes())
    
    classification = attrs['classification']
    if classification.startswith('NOGO'):
        classification = 'NOGO'
    label = CLASSIFICATION_LABELS[classification]
    label_feature = create_int64_feature(label)
    
    clip_id = attrs['clip_id']
    clip_id_feature = create_int64_feature(clip_id)
    
    if len(waveform) != int(round(EXAMPLE_DURATION * EXAMPLE_SAMPLE_RATE)):
        print(f'Unexpected waveform length {len(waveform)}.')
        
    features = tf.train.Features(
        feature={
            'waveform': waveform_feature,
            'label': label_feature,
            'clip_id': clip_id_feature,
        })
    
    return tf.train.Example(features=features)


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def show_clip_set_file_paths(classification, file_paths):
    print(classification, file_paths)
    

if __name__ == '__main__':
    main()
