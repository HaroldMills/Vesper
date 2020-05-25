"""Creates coarse classifier training datasets from clip HDF5 files."""


from collections import defaultdict
from pathlib import Path
import itertools
import math
import os
import random
import resource
import time

import h5py
import numpy as np
# import resampy
import tensorflow as tf

from vesper.util.bunch import Bunch
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.signal.resampling_utils as resampling_utils
import vesper.util.yaml_utils as yaml_utils


VALIDATION_FRACTION = .1
TEST_FRACTION = .1

CALL_TYPE = 'Tseep'

DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NFC Time Bounds Marker 1.0/')

INPUT_DIR_PATH = DATA_DIR_PATH / 'HDF5 Files' / CALL_TYPE

THRUSH_INPUT_FILE_NAMES = ''

TSEEP_INPUT_FILE_NAMES = '''
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Angela.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Bear.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Bell Crossing.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Darby.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Dashiell.h5
'''.strip().split('\n')

INPUT_FILE_NAMES = {
    'Thrush': THRUSH_INPUT_FILE_NAMES,
    'Tseep': TSEEP_INPUT_FILE_NAMES,
}[CALL_TYPE]

OUTPUT_SAMPLE_RATE = 24000

OUTPUT_DIR_PATH = DATA_DIR_PATH / 'Datasets' / CALL_TYPE
OUTPUT_FILE_NAME_FORMAT = '{}_{}_{:04d}.tfrecords'
OUTPUT_FILE_SIZE = 10000  # examples


def main():
    
    create_tfrecord_files()
      
    # test_get_dataset_clips()
    
    
def create_tfrecord_files():
    
    for input_file_name in INPUT_FILE_NAMES:
        
        # Get clip IDs from input file.
        input_file_path = INPUT_DIR_PATH / input_file_name
        file_ = h5py.File(input_file_path, 'r')
        clip_group = file_['clips']
        clip_ids = list(clip_group.keys())
        
        # Shuffle IDs.
        shuffled_clip_ids = np.random.permutation(clip_ids)
        
        # Partition shuffled IDs for training, validation, and test datasets.
        train_clip_ids, val_clip_ids, test_clip_ids = \
            partition_clip_ids(shuffled_clip_ids)
        
        # Create tfrecord files.
        file_name_prefix = input_file_path.stem
        create_tfrecord_files_aux(
            file_name_prefix, 'Training', clip_group, train_clip_ids)
        create_tfrecord_files_aux(
            file_name_prefix, 'Validation', clip_group, val_clip_ids)
        create_tfrecord_files_aux(
            file_name_prefix, 'Test', clip_group, test_clip_ids)
        
        
def partition_clip_ids(ids):
    
    clip_count = len(ids)
    
    val_start_index = get_subset_start_index(
        clip_count, VALIDATION_FRACTION + TEST_FRACTION)
    
    test_start_index = get_subset_start_index(clip_count, TEST_FRACTION)
    
    train_ids = ids[:val_start_index]
    val_ids = ids[val_start_index:test_start_index]
    test_ids = ids[test_start_index:]
    
    return train_ids, val_ids, test_ids

    
def get_subset_start_index(clip_count, offset):
    return int(round(clip_count * (1 - offset)))


def create_tfrecord_files_aux(
        file_name_prefix, dataset_name, clip_group, clip_ids):
    
    output_dir_path = OUTPUT_DIR_PATH / dataset_name
    
    print(f'{output_dir_path}')
    
    start_time = time.time()
    
    clip_count = len(clip_ids)
    file_count = int(math.ceil(clip_count / OUTPUT_FILE_SIZE))
    
    clip_num = 0
    file_num = 0
    
    while clip_num != clip_count:
        
        file_path = get_output_file_path(
            file_name_prefix, dataset_name, file_num)
        
        end_clip_num = min(clip_num + OUTPUT_FILE_SIZE, clip_count)
        file_clip_ids = clip_ids[clip_num:end_clip_num]
        
        print(
            f'    Writing {len(file_clip_ids)} clips to file "{file_path}" '
            f'(file {file_num + 1} of {file_count})...')
    
        write_output_file(clip_group, file_clip_ids, file_path)
               
        clip_num = end_clip_num
        file_num += 1
        
    end_time = time.time()
    delta = end_time - start_time
    rate = len(clip_ids) / delta
    print(
        f'    Wrote {len(clip_ids)} {dataset_name} clips to {file_count} '
        f'files in {delta:.1f} seconds, a rate of {rate:.1f} clips per '
        f'second.')


def get_output_file_path(file_name_prefix, dataset_name, file_num):
    
    file_name = OUTPUT_FILE_NAME_FORMAT.format(
        file_name_prefix, dataset_name, file_num)
    
    return OUTPUT_DIR_PATH / dataset_name / file_name


def write_output_file(clip_group, clip_ids, file_path):
    
    print('        Creating TF examples...')
    
    examples = create_tf_examples(clip_group, clip_ids)
    
    print('        Writing TF examples to file...')
    
    os_utils.create_parent_directory(file_path)
    with tf.io.TFRecordWriter(str(file_path)) as writer:
        for example in examples:
            writer.write(example.SerializeToString())
              
    print('        Done.')
        
        
def create_tf_examples(clip_group, clip_ids):
    return [create_tf_example(clip_group, i) for i in clip_ids]
    

def create_tf_example(clip_group, clip_id):
    
    clip = clip_group[clip_id]
    
    samples, call_start_index, call_end_index = get_clip_data(clip)
    
    samples_feature = create_bytes_feature(samples.tobytes())
    clip_id_feature = create_int64_feature(int(clip_id))
    start_index_feature = create_int64_feature(call_start_index)
    end_index_feature = create_int64_feature(call_end_index)
    
    features = tf.train.Features(
        feature={
            'samples': samples_feature,
            'clip_id': clip_id_feature,
            'call_start_index': start_index_feature,
            'call_end_index': end_index_feature
        })
     
    return tf.train.Example(features=features)


def get_clip_data(clip):
    
    samples = clip[:]
    
    attrs = clip.attrs
    
    extraction_start_index = attrs['extraction_start_index']
    call_start_index = attrs['call_start_index'] - extraction_start_index
    call_end_index = attrs['call_end_index'] - extraction_start_index
    
    # Resample if needed.
    sample_rate = attrs['sample_rate']
    if sample_rate != OUTPUT_SAMPLE_RATE:
        samples = resampling_utils.resample_to_24000_hz(samples, sample_rate)
        call_start_index = adjust_index(
            call_start_index, sample_rate, OUTPUT_SAMPLE_RATE)
        call_end_index = adjust_index(
            call_end_index, sample_rate, OUTPUT_SAMPLE_RATE)
        
    return samples, call_start_index, call_end_index
    

def adjust_index(index, old_sample_rate, new_sample_rate):
    return int(round(index * (new_sample_rate / old_sample_rate)))


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
 
 
def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))
 

# def get_inputs():
#     return [get_input(*p) for p in enumerate(INPUT_FILE_NAMES)]
# 
# 
# def get_input(input_num, file_name):
#     
#     file_path = INPUT_DIR_PATH / file_name
#     file_ = h5py.File(file_path, 'r')
#     clips_group = file_['clips']
#     
#     return Bunch(
#         num=input_num,
#         file_path=file_path,
#         file=file_,
#         clips_group=clips_group)
# 
# 
# def get_clip_metadata(inputs):
#     
#     from scripts.detector_eval.manual.station_night_sets import \
#         NON_TRAINING_STATION_NIGHTS
#             
#     start_time = time.time()
#     
#     filter_ = StationNightClipFilter(NON_TRAINING_STATION_NIGHTS)
#     
#     num_inputs = len(inputs)
#     pairs = []
#     for input_ in inputs:
#         print((
#             '    Reading clip metadata from file "{}" (file {} of '
#             '{})...').format(input_.file_path, input_.num + 1, num_inputs))
#         pair = get_file_clip_metadata(input_, filter_)
#         pairs.append(pair)
#     
#     # show_input_stats(inputs, pairs)
#     filter_.show_filtered_clip_counts()
#         
#     call_lists, noise_lists = zip(*pairs)
#     
#     calls = list(itertools.chain.from_iterable(call_lists))
#     noises = list(itertools.chain.from_iterable(noise_lists))
#     
#     end_time = time.time()
#     delta = end_time - start_time
#     num_calls = len(calls)
#     num_noises = len(noises)
#     num_clips = num_calls + num_noises
#     rate = num_clips / delta
#     print((
#         '    Read metadata for {} clips ({} calls and {} noises) from {} '
#         'input files in {:.1f} seconds, a rate of {:.1f} clips per '
#         'second.').format(
#             num_clips, num_calls, num_noises, len(inputs), delta, rate))
#     
#     return calls, noises
#         
#     
# def get_file_clip_metadata(input_, filter_):
#     
#     input_num = input_.num
#     
#     calls = []
#     noises = []
#     
#     for clip_id, hdf5_dataset in input_.clips_group.items():
#         
#         if filter_.filter(hdf5_dataset.attrs):
#             
#             clip = (input_num, clip_id)
#             
#             hdf5_classification = hdf5_dataset.attrs['classification']
#             
#             dataset_classification = \
#                 get_dataset_classification(hdf5_classification)
#     
#             if dataset_classification == 'Call':
#                 calls.append(clip)
#             
#             elif dataset_classification == 'Noise':
#                 noises.append(clip)
#             
#     return calls, noises
#     
#     
# def get_dataset_classification(hdf5_classification):
#     
#     for hdf5_classification_prefix, dataset_classification in \
#             DATASET_CLASSIFICATIONS:
#         
#         if hdf5_classification.startswith(hdf5_classification_prefix):
#             return dataset_classification
#         
#     # If we get here, no prefix of `classification` is included in
#     # `DATASET_CLASSIFICATIONS`.
#     return None
#         
#         
# def show_input_stats(inputs, pairs):
#     print('Input,Calls,Noises')
#     for input_, (calls, noises) in zip(inputs, pairs):
#         print('"{}",{},{}'.format(input_.file_path, len(calls), len(noises)))
# 
# 
# def get_dataset_clips(calls, noises, config):
# 
#     train_calls, val_calls, test_calls = \
#         get_dataset_clips_aux(calls, config, CLIP_TYPE_CALL)
#         
#     train_noises, val_noises, test_noises = \
#         get_dataset_clips_aux(noises, config, CLIP_TYPE_NOISE)
#         
#     return Bunch(
#         train=Bunch(calls=train_calls, noises=train_noises),
#         val=Bunch(calls=val_calls, noises=val_noises),
#         test=Bunch(calls=test_calls, noises=test_noises))
#         
#         
# def get_dataset_clips_aux(clips, config, clip_type_index):
#     
#     # Get training, validation, and test set sizes from configuration.
#     train_size = config.train_dataset_size[clip_type_index]
#     val_size = config.val_dataset_size[clip_type_index]
#     test_size = config.test_dataset_size[clip_type_index]
#     
#     num_clips_needed = 1 + val_size + test_size
#     if num_clips_needed > len(clips):
#         raise ValueError((
#             'Not enough clips for specified datasets. Needed {} '
#             'clips but got only {}.').format(num_clips_needed, len(clips)))
#     
#     # Shuffle clips in place.
#     random.shuffle(clips)
#     
#     # Divide clips into training, validation, and test segments.
#     test_start = -test_size
#     val_start = test_start - val_size
#     train_clips = clips[:val_start]
#     val_clips = clips[val_start:test_start]
#     test_clips = clips[test_start:]
#     
#     num_train_clips = len(train_clips)
#     
#     if num_train_clips < train_size:
#         # have fewer than requested number of training clips
#         
#         clip_type_name = CLIP_TYPE_NAMES[clip_type_index]
#         print((
#             'Repeating some or all of {} {} clips as needed to provide '
#             '{} training clips...').format(
#                 num_train_clips, clip_type_name, train_size))
#             
#         # Repeat clips as needed, shuffling copies.
#         n = train_size // num_train_clips
#         r = train_size % num_train_clips
#         lists = [get_shuffled_copy(train_clips) for _ in range(n)]
#         lists.append(train_clips[:r])
#         train_clips = list(itertools.chain.from_iterable(lists))
#         
#     elif num_train_clips > train_size:
#         # have more than requested number of training clips
#         
#         # Discard unneeded clips.
#         train_clips = train_clips[:train_size]
#         
#     return train_clips, val_clips, test_clips
#         
# 
# def get_shuffled_copy(x):
#     return random.sample(x, len(x))
# 
# 
# def show_dataset_stats(datasets):
#     print('Dataset,Calls,Noises')
#     show_dataset_stats_aux(datasets.train, 'Training')
#     show_dataset_stats_aux(datasets.val, 'Validation')
#     show_dataset_stats_aux(datasets.test, 'Test')
#     
#     
# def show_dataset_stats_aux(dataset, name):
#     print('{},{},{}'.format(name, len(dataset.calls), len(dataset.noises)))
#     
#     
# def create_output_files(inputs, datasets, config):
#     delete_output_directory(config.dataset_name_prefix)
#     create_output_files_aux(inputs, datasets.train, 'Training', config)
#     create_output_files_aux(inputs, datasets.val, 'Validation', config)
#     create_output_files_aux(inputs, datasets.test, 'Test', config)
#     
#     
# def delete_output_directory(dataset_name_prefix):
#     dir_path = OUTPUT_DIR_PATH / dataset_name_prefix
#     if os.path.exists(dir_path):
#         os_utils.delete_directory(str(dir_path))
#     
#     
# def create_output_files_aux(inputs, dataset, dataset_name, config):
#     
#     start_time = time.time()
#     
#     clips = dataset.calls + dataset.noises
#     random.shuffle(clips)
#     
#     num_clips = len(clips)
#     num_files = int(math.ceil(num_clips / OUTPUT_FILE_SIZE))
#     
#     clip_num = 0
#     file_num = 0
#     
#     while clip_num != num_clips:
#         
#         file_path = get_output_file_path(config, dataset_name, file_num)
#         
#         end_clip_num = min(clip_num + OUTPUT_FILE_SIZE, num_clips)
#         file_clips = clips[clip_num:end_clip_num]
#         
#         print(
#             '    Writing {} clips to file "{}" (file {} of {})...'.format(
#                 len(file_clips), file_path, file_num + 1, num_files))
#     
#         write_output_file(inputs, file_clips, file_path)
#                
#         clip_num = end_clip_num
#         file_num += 1
#         
#     end_time = time.time()
#     delta = end_time - start_time
#     rate = len(clips) / delta
#     print((
#         '    Wrote {} {} clips to {} files in {:.1f} seconds, a rate of '
#         '{:.1f} clips per second.').format(
#             len(clips), dataset_name, num_files, delta, rate))
#         
#         
# def close_input_files(inputs):
#     for i in inputs:
#         i.file.close()
#         
#         
# def get_output_file_path(config, dataset_name, file_num):
#     
#     prefix = config.dataset_name_prefix
#     
#     file_name = OUTPUT_FILE_NAME_FORMAT.format(prefix, dataset_name, file_num)
#     
#     return OUTPUT_DIR_PATH / prefix / dataset_name / file_name
# 
# 
# def write_output_file(inputs, file_clips, file_path):
#      
#     print('        closing and reopening input files...')
#      
#     # Close and reopen input HDF5 files. I do not understand why this
#     # is necessary, but without it the script sometimes quits with no
#     # error messages before it completes.
#     close_input_files(inputs)
#     inputs = get_inputs()
#     clip_groups = dict((i.num, i.clips_group) for i in inputs)
#      
#     print('        creating clip TF examples...')
#      
#     tf_examples = []
#     for input_num, clip_id in file_clips:
#         clip_ds = clip_groups[input_num][clip_id]
#         tf_example = create_tf_example(clip_ds)
#         tf_examples.append(tf_example)
#          
#     print('        writing TF examples to file...')
#      
#     os_utils.create_parent_directory(file_path)
#     with tf.python_io.TFRecordWriter(str(file_path)) as writer:
#         for tf_example in tf_examples:
#             writer.write(tf_example.SerializeToString())
#              
#     print('        done')
#      
# 
# def create_tf_example(clip_ds):
#     
#     waveform = clip_ds[:]
#     attrs = clip_ds.attrs
#     
#     sample_rate = attrs['sample_rate']
#     
#     # Trim waveform.
#     start_index = int(round(EXAMPLE_START_OFFSET * sample_rate))
#     length = int(round(EXAMPLE_DURATION * sample_rate))
#     waveform = waveform[start_index:start_index + length]
#     
#     # Resample if needed.
#     if sample_rate != EXAMPLE_SAMPLE_RATE:
#         # waveform = resampy.resample(
#         #    waveform, sample_rate, EXAMPLE_SAMPLE_RATE)
#         waveform = resampling_utils.resample_to_24000_hz(waveform, sample_rate)
#     
#     waveform_feature = create_bytes_feature(waveform.tobytes())
#     
#     classification = attrs['classification']
#     label = 1 if classification.startswith('Call') else 0
#     label_feature = create_int64_feature(label)
#     
#     clip_id = attrs['clip_id']
#     clip_id_feature = create_int64_feature(clip_id)
#     
#     features = tf.train.Features(
#         feature={
#             'waveform': waveform_feature,
#             'label': label_feature,
#             'clip_id': clip_id_feature
#         })
#     
#     return tf.train.Example(features=features)
# 
# 
# def create_bytes_feature(value):
#     return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
# 
# 
# def create_int64_feature(value):
#     return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))
# 
# 
# CREATE_DATASETS_TEST_CASES = [
#     Bunch(**case) for case in yaml_utils.load('''
# 
# - description: balanced inputs and datasets
#   num_calls: 10
#   num_noises: 10
#   train_dataset_size: [6, 6]
#   val_dataset_size: [2, 2]
#   test_dataset_size: [2, 2]
#   
# - description: more noises than calls, two calls repeated in training
#   num_calls: 8
#   num_noises: 10
#   train_dataset_size: [6, 6]
#   val_dataset_size: [2, 2]
#   test_dataset_size: [2, 2]
#   
# - description: more calls than noises, two noises repeated in training
#   num_calls: 10
#   num_noises: 8
#   train_dataset_size: [6, 6]
#   val_dataset_size: [2, 2]
#   test_dataset_size: [2, 2]
#   
# - description: more noises than calls, calls repeated twice in training
#   num_calls: 7
#   num_noises: 10
#   train_dataset_size: [6, 6]
#   val_dataset_size: [2, 2]
#   test_dataset_size: [2, 2]
# 
# - description: more noises than calls, calls repeat 2.5x in training
#   num_calls: 6
#   num_noises: 9
#   train_dataset_size: [5, 5]
#   val_dataset_size: [2, 2]
#   test_dataset_size: [2, 2]
# 
# - description: unbalanced datasets
#   num_calls: 10
#   num_noises: 10
#   train_dataset_size: [6, 4]
#   val_dataset_size: [2, 3]
#   test_dataset_size: [2, 3]
#   
# ''')]
# 
# 
# def test_get_dataset_clips():
#     
#     for case in CREATE_DATASETS_TEST_CASES:
#         
#         calls = create_test_clips(case.num_calls, 'c')
#         noises = create_test_clips(case.num_noises, 'n')
#         
#         datasets = get_dataset_clips(calls, noises, case)
#         
#         show_test_datasets(case, calls, noises, datasets)
# 
# 
# def create_test_clips(num_clips, prefix):
#     n0 = num_clips // 2
#     n1 = num_clips - n0
#     input_nums = ([0] * n0) + ([1] * n1)
#     clip_ids = ['{}{}'.format(prefix, i) for i in range(num_clips)]
#     return list(zip(input_nums, clip_ids))
#         
# 
# def show_test_datasets(case, calls, noises, datasets):
#     
#     print('For test case:')
#     print('    description: {}'.format(case.description))
#     print('    num_calls: {}'.format(case.num_calls))
#     print('    num_noises: {}'.format(case.num_noises))
#     print('    train_dataset_size: {}'.format(case.train_dataset_size))
#     print('    val_dataset_size: {}'.format(case.val_dataset_size))
#     print('    test_dataset_size: {}'.format(case.test_dataset_size))
#     
#     print()
#     
#     show_test_clips(calls, 'Calls')
#     show_test_clips(noises, 'Noises')
#     
#     print()
#     
#     show_test_dataset(datasets.train, 'Training')
#     show_test_dataset(datasets.val, 'Validation')
#     show_test_dataset(datasets.test, 'Test')
# 
# 
# def show_test_clips(clips, name):
#     print('{} are: {}'.format(name, clips))
#     
#     
# def show_test_dataset(dataset, name):
#     print('{} dataset:'.format(name))
#     print('   Calls: {}'.format(dataset.calls))
#     print('   Noises: {}'.format(dataset.noises))
#     print()
    
    
if __name__ == '__main__':
    main()
