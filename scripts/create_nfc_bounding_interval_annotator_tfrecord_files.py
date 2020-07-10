"""Creates NFC time bound marker datasets from clip HDF5 files."""


from pathlib import Path
import time

import h5py
import numpy as np
import tensorflow as tf

import vesper.util.os_utils as os_utils
import vesper.signal.resampling_utils as resampling_utils


VALIDATION_FRACTION = .1
TEST_FRACTION = .01

CALL_TYPE = 'Tseep'

DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'NFC Bounding Interval Annotator 1.0/')

INPUT_DIR_PATH = DATA_DIR_PATH / 'HDF5 Files' / CALL_TYPE

THRUSH_INPUT_FILE_NAMES = ''

TSEEP_INPUT_FILE_NAMES = '''
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Angela.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Bear.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Bell Crossing.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Darby.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Dashiell.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Davies.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Deer Mountain.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Floodplain.h5
Tseep_2017 MPG Ranch 30k_Old Bird Redux 1.1_Florence.h5
'''.strip().split('\n')

INPUT_FILE_NAMES = {
    'Thrush': THRUSH_INPUT_FILE_NAMES,
    'Tseep': TSEEP_INPUT_FILE_NAMES,
}[CALL_TYPE]

OUTPUT_SAMPLE_RATE = 24000

OUTPUT_DIR_PATH = DATA_DIR_PATH / 'Datasets' / CALL_TYPE
OUTPUT_FILE_NAME_FORMAT = '{}_{}.tfrecords'


def main():
    
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
        create_tfrecord_file(
            file_name_prefix, 'Training', clip_group, train_clip_ids)
        create_tfrecord_file(
            file_name_prefix, 'Validation', clip_group, val_clip_ids)
        create_tfrecord_file(
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


def create_tfrecord_file(file_name_prefix, dataset_name, clip_group, clip_ids):
    
    start_time = time.time()
    
    file_path = get_output_file_path(file_name_prefix, dataset_name)

    print(f'Writing {len(clip_ids)} clips to file "{file_path}"...')
    examples = create_tf_examples(clip_group, clip_ids)
    
    os_utils.create_parent_directory(file_path)
    with tf.io.TFRecordWriter(str(file_path)) as writer:
        for example in examples:
            writer.write(example.SerializeToString())
             
    end_time = time.time()
    delta = end_time - start_time
    rate = len(clip_ids) / delta
    print(
        f'    Wrote {len(clip_ids)} {dataset_name} clips in {delta:.1f} '
        f'seconds, a rate of {rate:.1f} clips per second.')


def create_tf_examples(clip_group, clip_ids):
    return [create_tf_example(clip_group, i) for i in clip_ids]
    

def create_tf_example(clip_group, clip_id):
    
    clip = clip_group[clip_id]
    
    (waveform, clip_start_index, clip_end_index, call_start_index,
        call_end_index) = get_clip_data(clip)
    
    clip_id_feature = create_int64_feature(int(clip_id))
    waveform_feature = create_bytes_feature(waveform.tobytes())
    clip_start_index_feature = create_int64_feature(clip_start_index)
    clip_end_index_feature = create_int64_feature(clip_end_index)
    call_start_index_feature = create_int64_feature(call_start_index)
    call_end_index_feature = create_int64_feature(call_end_index)
    
    features = tf.train.Features(
        feature={
            'clip_id': clip_id_feature,
            'waveform': waveform_feature,
            'clip_start_index': clip_start_index_feature,
            'clip_end_index': clip_end_index_feature,
            'call_start_index': call_start_index_feature,
            'call_end_index': call_end_index_feature,
        })
     
    return tf.train.Example(features=features)


def get_clip_data(clip):
    
    waveform = clip[:]
    
    attrs = clip.attrs
    
    extraction_start_index = attrs['extraction_start_index']
    clip_start_index = attrs['clip_start_index'] - extraction_start_index
    clip_end_index = clip_start_index + attrs['clip_length']
    call_start_index = attrs['call_start_index'] - extraction_start_index
    call_end_index = attrs['call_end_index'] - extraction_start_index
    
    # Resample if needed.
    sample_rate = attrs['sample_rate']
    if sample_rate != OUTPUT_SAMPLE_RATE:
        waveform = resampling_utils.resample_to_24000_hz(waveform, sample_rate)
        clip_start_index = adjust_index(
            clip_start_index, sample_rate, OUTPUT_SAMPLE_RATE)
        clip_end_index = adjust_index(
            clip_end_index, sample_rate, OUTPUT_SAMPLE_RATE)
        call_start_index = adjust_index(
            call_start_index, sample_rate, OUTPUT_SAMPLE_RATE)
        call_end_index = adjust_index(
            call_end_index, sample_rate, OUTPUT_SAMPLE_RATE)
        
    return (
        waveform, clip_start_index, clip_end_index, call_start_index,
        call_end_index)
    

def adjust_index(index, old_sample_rate, new_sample_rate):
    return int(round(index * (new_sample_rate / old_sample_rate)))


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
 
 
def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))
    
    
def get_output_file_path(file_name_prefix, dataset_name):
    
    file_name = OUTPUT_FILE_NAME_FORMAT.format(
        file_name_prefix, dataset_name)
    
    return OUTPUT_DIR_PATH / dataset_name / file_name


if __name__ == '__main__':
    main()
