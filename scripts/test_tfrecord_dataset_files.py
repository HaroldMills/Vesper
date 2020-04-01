"""
Script that shows how to write clip classification training examples to
multiple TFRecord files and then read the files as a single TensorFlow
`Dataset`.
"""


from pathlib import Path

import numpy as np
import tensorflow as tf


DATA_DIR_PATH = Path('/Users/harold/Desktop')
DATA_FILE_NAME_FORMAT = 'dataset_part_{}.tfrecords'

EXAMPLE_FEATURES = {
    'samples': tf.FixedLenFeature((), tf.string, default_value=''),
    'label': tf.FixedLenFeature((), tf.int64, default_value=0)
}   


def main():
    write_data_files()
    dataset = create_tf_dataset()
    show_dataset(dataset)
    
    
def write_data_files():
    write_data_file(0, 0, 4)
    write_data_file(1, 4, 4)


def write_data_file(file_num, start_index, num_examples):
    
    file_path = create_data_file_path(str(file_num))
    examples = create_examples(start_index, num_examples)
    
    with tf.python_io.TFRecordWriter(file_path) as writer:
        
        for example in examples:
            
            tf_example = create_tf_example(*example)
            writer.write(tf_example.SerializeToString())
            
      
def create_data_file_path(file_num):
    file_name = DATA_FILE_NAME_FORMAT.format(file_num)
    return str(DATA_DIR_PATH / file_name)
    

def create_examples(start_index, num_examples):
    
    n = num_examples
    dtype = '<i2'
    row = np.arange(n, dtype=dtype)
    col = np.arange(start_index, start_index + n, dtype=dtype).reshape((n, 1))
    samples = row + col
    
    labels = np.arange(n)
    
    return list(zip(samples, labels))
    
 
def create_tf_example(samples, label):
    
    samples_feature = create_bytes_feature(samples.tobytes())
    label_feature = create_int64_feature(label)
    
    features = tf.train.Features(
        feature={
            'samples': samples_feature,
            'label': label_feature
        })
    
    return tf.train.Example(features=features)


def create_bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def create_int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def create_tf_dataset():
    
    file_path_pattern = create_data_file_path('*')
    
    # Get file paths matching pattern. Sort the paths for consistency.
    file_paths = sorted(tf.gfile.Glob(file_path_pattern))
    
    return tf.data.TFRecordDataset(file_paths).map(parse_example)
            
        
def parse_example(example_proto):
    
    example = tf.parse_single_example(example_proto, EXAMPLE_FEATURES)
    
    bytes_ = example['samples']
    samples = tf.decode_raw(bytes_, out_type=tf.int16, little_endian=True)
    
    # Extract portion of clip samples.
    samples = samples[1:3]
    
    label = example['label']
    
    return samples, label


def show_dataset(dataset):
    
    print('output types', dataset.output_types)
    print('output_shapes', dataset.output_shapes)
    
    iterator = dataset.make_one_shot_iterator()
    next_element = iterator.get_next()
     
    with tf.Session() as sess:
        
        while True:
            
            try:
                
                samples, label = sess.run(next_element)
                
                samples_class = samples.__class__.__name__
                label_class = label.__class__.__name__
                
                print(
                    'samples {} {}, label {} {}'.format(
                        samples_class, samples, label_class, label))
                
            except tf.errors.OutOfRangeError:
                print('end of dataset')
                break

     
if __name__ == '__main__':
    main()
