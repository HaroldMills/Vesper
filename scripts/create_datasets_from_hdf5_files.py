"""Creates coarse classifier training datasets from clip HDF5 files."""


from pathlib import Path
import itertools
import math
import os
import random
import time

import h5py
import resampy
import tensorflow as tf

from vesper.util.bunch import Bunch
import vesper.util.os_utils as os_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Support creating multiple datasets in one run.
# TODO: Replace `dataset_name_prefix` and `detector_name` with type and size.


DATASET_NAME_PREFIX = 'Thrush 100K'

DATASET_CONFIGS = yaml_utils.load('''

- dataset_name_prefix: Thrush 20K
  detector_name: Thrush
  train_dataset_size: [6000, 6000]
  val_dataset_size: [2000, 2000]
  test_dataset_size: [2000, 2000]
  
- dataset_name_prefix: Thrush 100K
  detector_name: Tseep
  train_dataset_size: [36000, 36000]
  val_dataset_size: [2000, 2000]
  test_dataset_size: [2000, 2000]
  
- dataset_name_prefix: Thrush 1M
  detector_name: Thrush
  train_dataset_size: [496000, 496000]
  val_dataset_size: [2000, 2000]
  test_dataset_size: [2000, 2000]

- dataset_name_prefix: Tseep 3K
  detector_name: Tseep
  train_dataset_size: [2000, 2000]
  val_dataset_size: [500, 500]
  test_dataset_size: [500, 500]
    
- dataset_name_prefix: Tseep 20K
  detector_name: Tseep
  train_dataset_size: [6000, 6000]
  val_dataset_size: [2000, 2000]
  test_dataset_size: [2000, 2000]
    
- dataset_name_prefix: Tseep 100K
  detector_name: Tseep
  train_dataset_size: [40000, 40000]
  val_dataset_size: [5000, 5000]
  test_dataset_size: [5000, 5000]
  
- dataset_name_prefix: Tseep 340K
  detector_name: Tseep
  train_dataset_size: [158579, 158579]
  val_dataset_size: [5000, 5000]
  test_dataset_size: [5000, 5000]
  
- dataset_name_prefix: Tseep 1M
  detector_name: Tseep
  train_dataset_size: [480000, 480000]
  val_dataset_size: [10000, 10000]
  test_dataset_size: [10000, 10000]
  
''')

INPUT_DIR_PATH = Path(
    '/Volumes/NFC Data 2/NFC/Data/Vesper ML/Datasets/Clip HDF5 Files')

# INPUT_FILE_NAMES = '''
# Tseep_MPG_Angela_2017_1.h5
# '''.split('\n')[1:-1]

# INPUT_FILE_NAMES = '''
# Tseep_MPG_Angela_2017_1.h5
# Tseep_MPG_Bear_2017_1.h5
# Tseep_MPG_Bell Crossing_2017_1.h5
# Tseep_MPG_Darby_2017_1.h5
# Tseep_MPG_Dashiell_2017_1.h5
# Tseep_MPG_Davies_2017_1.h5
# Tseep_MPG_Deer Mountain_2017_1.h5
# Tseep_MPG_Floodplain_2017_1.h5
# '''.split('\n')[1:-1]

# INPUT_FILE_NAMES = '''
# Tseep_MPG_Angela_2017_1.h5
# Tseep_MPG_Bear_2017_1.h5
# Tseep_MPG_Bell Crossing_2017_1.h5
# Tseep_MPG_Darby_2017_1.h5
# Tseep_MPG_Dashiell_2017_1.h5
# Tseep_MPG_Davies_2017_1.h5
# Tseep_MPG_Deer Mountain_2017_1.h5
# Tseep_MPG_Floodplain_2017_1.h5
# Tseep_MPG_Florence_2017_1.h5
# Tseep_MPG_KBK_2017_1.h5
# Tseep_MPG_Lilo_2017_1.h5
# Tseep_MPG_Nelson_2017_1.h5
# Tseep_MPG_North_2017_1.h5
# Tseep_MPG_Oxbow_2017_1.h5
# Tseep_MPG_Powell_2017_1.h5
# Tseep_MPG_Reed_2017_1.h5
# Tseep_MPG_Ridge_2017_1.h5
# Tseep_MPG_Seeley_2017_1.h5
# Tseep_MPG_Sheep Camp_2017_1.h5
# Tseep_MPG_St Mary_2017_1.h5
# Tseep_MPG_Sula Peak_2017_1.h5
# Tseep_MPG_Teller_2017_1.h5
# Tseep_MPG_Troy_2017_1.h5
# Tseep_MPG_Walnut_2017_1.h5
# Tseep_MPG_Weber_2017_1.h5
# Tseep_MPG_Willow_2017_1.h5
# '''.split('\n')[1:-1]

INPUT_FILE_NAMES = '''
Thrush_MPG_Angela_2017_1.h5
Thrush_MPG_Bear_2017_1.h5
Thrush_MPG_Bell Crossing_2017_1.h5
Thrush_MPG_Darby_2017_1.h5
Thrush_MPG_Dashiell_2017_1.h5
Thrush_MPG_Davies_2017_1.h5
Thrush_MPG_Deer Mountain_2017_1.h5
Thrush_MPG_Floodplain_2017_1.h5
Thrush_MPG_Florence_2017_1.h5
Thrush_MPG_KBK_2017_1.h5
Thrush_MPG_Lilo_2017_1.h5
Thrush_MPG_Nelson_2017_1.h5
Thrush_MPG_North_2017_1.h5
Thrush_MPG_Oxbow_2017_1.h5
Thrush_MPG_Powell_2017_1.h5
Thrush_MPG_Reed_2017_1.h5
Thrush_MPG_Ridge_2017_1.h5
Thrush_MPG_Seeley_2017_1.h5
Thrush_MPG_Sheep Camp_2017_1.h5
Thrush_MPG_St Mary_2017_1.h5
Thrush_MPG_Sula Peak_2017_1.h5
Thrush_MPG_Teller_2017_1.h5
Thrush_MPG_Troy_2017_1.h5
Thrush_MPG_Walnut_2017_1.h5
Thrush_MPG_Weber_2017_1.h5
Thrush_MPG_Willow_2017_1.h5
'''.split('\n')[1:-1]

# Thrush
EXAMPLE_START_OFFSET = .1   # seconds
EXAMPLE_DURATION = .55      # seconds

# Tseep
# EXAMPLE_START_OFFSET = .1   # seconds
# EXAMPLE_DURATION = .4       # seconds

EXAMPLE_SAMPLE_RATE = 24000

CLIP_TYPE_NAMES = ('call', 'noise')
CLIP_TYPE_CALL = 0
CLIP_TYPE_NOISE = 1

OUTPUT_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/Datasets/Coarse Classification')
OUTPUT_FILE_NAME_FORMAT = '{}_{}_{:04d}.tfrecords'
OUTPUT_FILE_SIZE = 10000  # examples


'''
Can compute spectrograms with TensorFlow if we wish. Would it be faster
or not? This should be fairly easy to test, I think. Write a test program
to:

1. Generate a sinusoidal test signal, an hour long, say.
2. Compute a spectrogram of it.

Classification pipeline:

1. Get clip waveform at appropriate sample rate.
2. Compute spectrogram.
3. Slice spectrogram.
4. Input spectrogram to neural network.

I think it would be best for detection and classification datasets (i.e.
sets of TFRecord files) to contain audio clips at the appropriate sample
rate rather than spectrograms, and to compute spectrograms in the TensorFlow
graph. Some advantages to this approach:

1. It makes it easier to experiment with various spectrogram settings. If
the dataset contains spectrograms instead of waveforms, we have to generate
a separate dataset for every set of spectrogram settings we want to try.

2. It makes it easier to ensure consistency in spectrogram computation
in training and inference. When the spectrogram computation is part of
the TensorFlow graph, it is automatically the same in training and
inference since they share the graph. When it is not part of the graph,
the spectrogram computation for dataset creation and inference can get
out of sync.

3. If we use TensorFlow for the spectrogram computation, it can happen
on a GPU.

Potential disadvantages of computing spectrograms in the TensorFlow graph:

1. We have to compute spectrograms on the fly during training, recomputing
the same spectrogram each time we see an example, instead of computing a
spectrogram for each example just once when we create the dataset.

2. TensorFlow spectrogram computation may (or may not) be slower than Vesper
spectrogram.

We can look into these potential disadvantages by timing spectrogram
computations and training. If it turns out that TensorFlow spectrograms
are problematically slow, perhaps we can use our spectrogram from within
TensorFlow. 

Tasks:

1. Compare speed of TensorFlow spectrogram to speed of Vesper spectrogram.

2. Create two versions of a modest-sized TFRecords dataset, one containing
waveforms and the other spectrograms. Compare speed of training with waveform
dataset to speed of training with spectrogram dataset.
'''


def main():
    
    create_datasets(DATASET_NAME_PREFIX)
      
    # test_get_dataset_clips()
    
    
def create_datasets(dataset_name_prefix):
    
    # Get dataset configutation.
    configs = [Bunch(**c) for c in DATASET_CONFIGS]
    configs = dict((c.dataset_name_prefix, c) for c in configs)
    config = configs[dataset_name_prefix]
      
    inputs = get_inputs()
    
    print('Reading clip metadata from input files...')
    calls, noises = get_clip_metadata(inputs)
      
    print('Assigning clips to datasets...')
    datasets = get_dataset_clips(calls, noises, config)
     
    # show_dataset_stats(datasets)
      
    print('Writing clips to output files...')
    create_output_files(inputs, datasets, config)
    
    close_input_files(inputs)
    
    print('Done.')


def get_inputs():
    return [get_input(*p) for p in enumerate(INPUT_FILE_NAMES)]


def get_input(input_num, file_name):
    
    file_path = INPUT_DIR_PATH / file_name
    file_ = h5py.File(file_path, 'r')
    clips_group = file_['clips']
    
    return Bunch(
        num=input_num,
        file_path=file_path,
        file=file_,
        clips_group=clips_group)


def get_clip_metadata(inputs):
    
    start_time = time.time()
    
    num_inputs = len(inputs)
    pairs = []
    for input_ in inputs:
        print((
            '    Reading clip metadata from file "{}" (file {} of '
            '{})...').format(input_.file_path, input_.num + 1, num_inputs))
        pair = get_file_clip_metadata(input_)
        pairs.append(pair)
    
    # show_input_stats(inputs, pairs)
        
    call_lists, noise_lists = zip(*pairs)
    
    calls = list(itertools.chain.from_iterable(call_lists))
    noises = list(itertools.chain.from_iterable(noise_lists))
    
    end_time = time.time()
    delta = end_time - start_time
    num_clips = len(calls) + len(noises)
    rate = num_clips / delta
    print((
        '    Read metadata for {} clips from {} input files in {:.1f} '
        'seconds, a rate of {:.1f} clips per second.').format(
            num_clips, len(inputs), delta, rate))
    
    return calls, noises
        
    
def get_file_clip_metadata(input_):
    
    input_num = input_.num
    
    calls = []
    noises = []
    
    for clip_id, dataset in input_.clips_group.items():
        
        clip = (input_num, clip_id)
        
        classification = dataset.attrs['classification']
        
        if classification.startswith('Call'):
            calls.append(clip)
            
        elif classification.startswith('Noise'):
            noises.append(clip)
            
    return calls, noises
    
    
def show_input_stats(inputs, pairs):
    print('Input,Calls,Noises')
    for input_, (calls, noises) in zip(inputs, pairs):
        print('"{}",{},{}'.format(input_.file_path, len(calls), len(noises)))


def get_dataset_clips(calls, noises, config):

    train_calls, val_calls, test_calls = \
        get_dataset_clips_aux(calls, config, CLIP_TYPE_CALL)
        
    train_noises, val_noises, test_noises = \
        get_dataset_clips_aux(noises, config, CLIP_TYPE_NOISE)
        
    return Bunch(
        train=Bunch(calls=train_calls, noises=train_noises),
        val=Bunch(calls=val_calls, noises=val_noises),
        test=Bunch(calls=test_calls, noises=test_noises))
        
        
def get_dataset_clips_aux(clips, config, clip_type_index):
    
    # Get training, validation, and test set sizes from configuration.
    train_size = config.train_dataset_size[clip_type_index]
    val_size = config.val_dataset_size[clip_type_index]
    test_size = config.test_dataset_size[clip_type_index]
    
    num_clips_needed = 1 + val_size + test_size
    if num_clips_needed > len(clips):
        raise ValueError((
            'Not enough clips for specified datasets. Needed {} '
            'clips but got only {}.').format(num_clips_needed, len(clips)))
    
    # Shuffle clips in place.
    random.shuffle(clips)
    
    # Divide clips into training, validation, and test segments.
    test_start = -test_size
    val_start = test_start - val_size
    train_clips = clips[:val_start]
    val_clips = clips[val_start:test_start]
    test_clips = clips[test_start:]
    
    num_train_clips = len(train_clips)
    
    if num_train_clips < train_size:
        # have fewer than requested number of training clips
        
        clip_type_name = CLIP_TYPE_NAMES[clip_type_index]
        print((
            'Repeating some or all of {} {} clips as needed to provide '
            '{} training clips...').format(
                num_train_clips, clip_type_name, train_size))
            
        # Repeat clips as needed, shuffling copies.
        n = train_size // num_train_clips
        r = train_size % num_train_clips
        lists = [get_shuffled_copy(train_clips) for _ in range(n)]
        lists.append(train_clips[:r])
        train_clips = list(itertools.chain.from_iterable(lists))
        
    elif num_train_clips > train_size:
        # have more than requested number of training clips
        
        # Discard unneeded clips.
        train_clips = train_clips[:train_size]
        
    return train_clips, val_clips, test_clips
        

def get_shuffled_copy(x):
    return random.sample(x, len(x))


def show_dataset_stats(datasets):
    print('Dataset,Calls,Noises')
    show_dataset_stats_aux(datasets.train, 'Training')
    show_dataset_stats_aux(datasets.val, 'Validation')
    show_dataset_stats_aux(datasets.test, 'Test')
    
    
def show_dataset_stats_aux(dataset, name):
    print('{},{},{}'.format(name, len(dataset.calls), len(dataset.noises)))
    
    
def close_input_files(inputs):
    for i in inputs:
        i.file.close()
        
        
def create_output_files(inputs, datasets, config):
    delete_output_directory(config.dataset_name_prefix)
    create_output_files_aux(inputs, datasets.train, 'Training', config)
    create_output_files_aux(inputs, datasets.val, 'Validation', config)
    create_output_files_aux(inputs, datasets.test, 'Test', config)
    
    
def delete_output_directory(dataset_name_prefix):
    dir_path = OUTPUT_DIR_PATH / dataset_name_prefix
    if os.path.exists(dir_path):
        os_utils.delete_directory(str(dir_path))
    
    
def create_output_files_aux(inputs, dataset, dataset_name, config):
    
    start_time = time.time()

    clip_groups = dict((i.num, i.clips_group) for i in inputs)
    
    clips = dataset.calls + dataset.noises
    random.shuffle(clips)
    
    num_clips = len(clips)
    num_files = int(math.ceil(num_clips / OUTPUT_FILE_SIZE))
    
    clip_num = 0
    file_num = 0
    
    while clip_num != num_clips:
        
        file_path = get_output_file_path(config, dataset_name, file_num)
        
        end_clip_num = min(clip_num + OUTPUT_FILE_SIZE, num_clips)
        file_clips = clips[clip_num:end_clip_num]
        
        print(
            '    Writing {} clips to file "{}" (file {} of {})...'.format(
                len(file_clips), file_path, file_num + 1, num_files))
    
        write_output_file(file_path, file_clips, clip_groups, config)
        
        clip_num = end_clip_num
        file_num += 1
        
    end_time = time.time()
    delta = end_time - start_time
    rate = len(clips) / delta
    print((
        '    Wrote {} {} clips to {} files in {:.1f} seconds, a rate of '
        '{:.1f} clips per second.').format(
            len(clips), dataset_name, num_files, delta, rate))
        
        
def get_output_file_path(config, dataset_name, file_num):
    
    prefix = config.dataset_name_prefix
    
    file_name = OUTPUT_FILE_NAME_FORMAT.format(prefix, dataset_name, file_num)
    
    return OUTPUT_DIR_PATH / prefix / dataset_name / file_name


def write_output_file(file_path, clips, clip_groups, config):
    
    os_utils.create_parent_directory(file_path)
    
    with tf.python_io.TFRecordWriter(str(file_path)) as writer:
        
        for input_num, clip_id in clips:
             
            ds = clip_groups[input_num][clip_id]
            tf_example = create_tf_example(ds)
            writer.write(tf_example.SerializeToString())
     

def create_tf_example(ds):
    
    waveform = ds[:]
    attrs = ds.attrs
    
    sample_rate = attrs['sample_rate']
    
    # Trim waveform.
    start_index = int(round(EXAMPLE_START_OFFSET * sample_rate))
    length = int(round(EXAMPLE_DURATION * sample_rate))
    waveform = waveform[start_index:start_index + length]
    
    # Resample if needed.
    if sample_rate != EXAMPLE_SAMPLE_RATE:
        waveform = resampy.resample(waveform, sample_rate, EXAMPLE_SAMPLE_RATE)
    
    waveform_feature = create_bytes_feature(waveform.tostring())
    
    classification = attrs['classification']
    label = 1 if classification.startswith('Call') else 0
    label_feature = create_int64_feature(label)
    
    clip_id = attrs['clip_id']
    clip_id_feature = create_int64_feature(clip_id)
    
    features = tf.train.Features(
        feature={
            'waveform': waveform_feature,
            'label': label_feature,
            'clip_id': clip_id_feature
        })
    
    return tf.train.Example(features=features)


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


CREATE_DATASETS_TEST_CASES = [
    Bunch(**case) for case in yaml_utils.load('''

- description: balanced inputs and datasets
  num_calls: 10
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more noises than calls, two calls repeated in training
  num_calls: 8
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more calls than noises, two noises repeated in training
  num_calls: 10
  num_noises: 8
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]
  
- description: more noises than calls, calls repeated twice in training
  num_calls: 7
  num_noises: 10
  train_dataset_size: [6, 6]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]

- description: more noises than calls, calls repeat 2.5x in training
  num_calls: 6
  num_noises: 9
  train_dataset_size: [5, 5]
  val_dataset_size: [2, 2]
  test_dataset_size: [2, 2]

- description: unbalanced datasets
  num_calls: 10
  num_noises: 10
  train_dataset_size: [6, 4]
  val_dataset_size: [2, 3]
  test_dataset_size: [2, 3]
  
''')]


def test_get_dataset_clips():
    
    for case in CREATE_DATASETS_TEST_CASES:
        
        calls = create_test_clips(case.num_calls, 'c')
        noises = create_test_clips(case.num_noises, 'n')
        
        datasets = get_dataset_clips(calls, noises, case)
        
        show_test_datasets(case, calls, noises, datasets)


def create_test_clips(num_clips, prefix):
    n0 = num_clips // 2
    n1 = num_clips - n0
    input_nums = ([0] * n0) + ([1] * n1)
    clip_ids = ['{}{}'.format(prefix, i) for i in range(num_clips)]
    return list(zip(input_nums, clip_ids))
        

def show_test_datasets(case, calls, noises, datasets):
    
    print('For test case:')
    print('    description: {}'.format(case.description))
    print('    num_calls: {}'.format(case.num_calls))
    print('    num_noises: {}'.format(case.num_noises))
    print('    train_dataset_size: {}'.format(case.train_dataset_size))
    print('    val_dataset_size: {}'.format(case.val_dataset_size))
    print('    test_dataset_size: {}'.format(case.test_dataset_size))
    
    print()
    
    show_test_clips(calls, 'Calls')
    show_test_clips(noises, 'Noises')
    
    print()
    
    show_test_dataset(datasets.train, 'Training')
    show_test_dataset(datasets.val, 'Validation')
    show_test_dataset(datasets.test, 'Test')


def show_test_clips(clips, name):
    print('{} are: {}'.format(name, clips))
    
    
def show_test_dataset(dataset, name):
    print('{} dataset:'.format(name))
    print('   Calls: {}'.format(dataset.calls))
    print('   Noises: {}'.format(dataset.noises))
    print()
    
    
if __name__ == '__main__':
    main()
