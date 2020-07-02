from collections import defaultdict
import datetime
import math
import time

from tensorflow.keras.layers import (
    BatchNormalization, Conv2D, Dense, Flatten, MaxPooling2D)
from tensorflow.keras.models import Sequential
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

from vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.inferrer \
    import Inferrer
from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator_utils \
    as annotator_utils
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.dataset_utils \
    as dataset_utils
import vesper.util.yaml_utils as yaml_utils


CLIP_TYPE = 'Tseep'

# TODO: Compute this from settings rather than hard-coding it.
EXAMPLE_SHAPE = (21, 33, 1)

TSEEP_SETTINGS = Settings(
    
    dataset_name='Tseep',
    
    waveform_sample_rate=24000,
    
    # `True` if and only if data augmentation is enabled during evaluation.
    # Data augmentation is always enabled during training (though some
    # individual augmentations can be turned on or off by settings below),
    # and it is always disabled during inference.
    evaluation_data_augmentation_enabled=False,
    
    # `True` if and only if the waveform time reversal data augmentation
    # is enabled. This augmentation reverses each waveform with
    # probability .5.
    waveform_time_reversal_data_augmentation_enabled=True,
    
    positive_probability=.25,
    
    waveform_slice_duration=.055,
    
    call_start_window_center_time=.0275,
    
    # call_start_window_duration=.005,
    call_start_window_duration=0.0001,

    # `True` if and only if the waveform amplitude scaling data
    # augmentation is enabled. This augmentation scales each waveform
    # randomly to distribute the waveform log RMS amplitudes uniformly
    # within a roughly 48 dB window.
    waveform_amplitude_scaling_data_augmentation_enabled=True,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=50,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=4000,
    spectrogram_end_freq=10000,
    
    # offset for converting inference value to spectrogram index
    call_bound_index_offset=8
    
)


'''
start_2020-06-23_15.10.16
window duration 52.5 ms
offset 9 spectra
    -172 1
    -80 1
    -16 1
    -13 1
    -5 2
    -4 2
    -3 5
    -2 10
    -1 85
    0 193
    1 102
    2 33
    3 29
    4 13
    5 7
    6 3
    7 3
    8 2
    10 1
    11 1
    14 1
    32 1
    42 1
    44 1
    499 0.2625250501002004 9.285993635172202
'''


def main():
    
    # test_bincount()
    
    # test_create_waveform_dataset_from_tensors()
    
    # test_create_waveform_dataset_from_tfrecord_files('Training')
    
    # test_create_training_dataset('Training')
    
    # test_create_inference_dataset()
    
    train_and_validate_annotator()
    
    # validate_annotator('start_2020-06-18_14.37.57')
    
    # validate_annotator('start_2020-06-22_14.02.02')
    
    # validate_annotator('start_2020-06-22_16.57.46')
    
    # validate_annotator('start_2020-06-22_17.13.30')
    
    # plot_first_gram('Validation', 'end_2020-06-10_17.27.22')
    # plot_first_gram('Validation', 'start_2020-06-10_12.13.39')
    
    # show_model_summary('start_2020-06-10_12.13.39')
    

def train_and_validate_annotator():
    model_name = create_model_name()
    train_annotator(model_name)
    validate_annotator(model_name)


def create_model_name():
    return datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')


def train_annotator(model_name):
    
    training_dataset = get_dataset('Training').batch(128)
    validation_dataset = get_dataset('Validation').batch(1)
    
    model = Sequential([
        
        Conv2D(16, (3, 3), activation='relu', input_shape=EXAMPLE_SHAPE),
        BatchNormalization(),
        # MaxPooling2D((1, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),
 
        Conv2D(16, (3, 3), activation='relu'),
        BatchNormalization(),
        # MaxPooling2D((1, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),

        Flatten(),
        
        # Dense(32, activation='relu'),
        # BatchNormalization(),
        
        Dense(16, activation='relu'),
        BatchNormalization(),
        
        Dense(1, activation='sigmoid')
        
    ])
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    model.summary()
    
    log_dir_path = annotator_utils.get_log_dir_path(CLIP_TYPE, model_name)
    callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir_path, histogram_freq=1)
     
    model.fit(
        training_dataset, epochs=50, steps_per_epoch=50, verbose=2,
        validation_data=validation_dataset, validation_steps=500,
        callbacks=[callback])
     
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        CLIP_TYPE, model_name)
    model.save(model_dir_path)
    
    save_model_settings(TSEEP_SETTINGS, model_name)


def get_dataset(name):
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    return dataset_utils.create_training_dataset(dir_path, TSEEP_SETTINGS)


def save_model_settings(settings, model_name):
    
    file_path = annotator_utils.get_model_settings_file_path(
        CLIP_TYPE, model_name)
    
    text = yaml_utils.dump(settings.__dict__, default_flow_style=False)
    
    file_path.write_text(text)


def validate_annotator(model_name):
    
    settings = TSEEP_SETTINGS
    
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        CLIP_TYPE, model_name)
    model = tf.keras.models.load_model(model_dir_path)
    
    model.summary()
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, 'Validation')
    dataset = dataset_utils.create_validation_dataset(dir_path, settings)
    
    dataset = dataset.take(500)
    
    inferrer = Inferrer(CLIP_TYPE)
    
    bounds = inferrer.get_call_bounds(dataset)
    
    start_diff_counts = defaultdict(int)
    end_diff_counts = defaultdict(int)
    
    for (inferred_start_index, inferred_end_index, dataset_start_index,
            dataset_end_index) in bounds:
        
        dataset_start_index = dataset_start_index.numpy()
        dataset_end_index = dataset_end_index.numpy()
        
        sample_rate = settings.waveform_sample_rate
        start_diff = _get_diff(
            inferred_start_index, dataset_start_index, sample_rate)
        end_diff = _get_diff(
            inferred_end_index, dataset_end_index, sample_rate)
        
        if start_diff is not None:
            start_diff_counts[start_diff] += 1
            end_diff_counts[end_diff] += 1
        
#         print(
#             start_diff, end_diff,
#             inferred_start_index, inferred_end_index,
#             dataset_start_index, dataset_end_index)

    _show_diff_counts('start', start_diff_counts)
    _show_diff_counts('end', end_diff_counts)
    _plot_diff_counts(start_diff_counts, end_diff_counts)
    
    
def _get_diff(inferred_index, dataset_index, sample_rate):
    
    if inferred_index is None:
        return None
    
    else:
        sample_count = inferred_index - dataset_index
        return int(round(1000 * sample_count / sample_rate))


def _show_diff_counts(name, counts):
    
    diffs = sorted(counts.keys())
    
    # Calculate difference mean and standard deviation.
    diff_sum = 0
    diff_sum_2 = 0
    for diff in diffs:
        count = counts[diff]
        diff_sum += count * diff
        diff_sum_2 += count * diff * diff
    total_count = sum(counts.values())
    diff_mean = diff_sum / total_count
    diff_std = math.sqrt(diff_sum_2 / total_count - diff_mean * diff_mean)
    
    print(f'{name} {total_count} {diff_mean} {diff_std}')
    
    print()
    
    
def _plot_diff_counts(start_diff_counts, end_diff_counts):
    
    figure, (start_axes, end_axes) = plt.subplots(2)
    
    _plot_diff_counts_aux(start_axes, 'Clip Starts', start_diff_counts)
    _plot_diff_counts_aux(end_axes, 'Clip Ends', end_diff_counts)
    
    plt.tight_layout()
    
    plt.show()
    
    
def _plot_diff_counts_aux(axes, title, counts):
    
    limit = 20
    x = np.arange(-limit, limit + 1)
    
    total_count = sum(counts.values())
    y = np.array([counts[d] for d in x]) / total_count
    
    axes.bar(x, y)
    axes.set_title(title)
    axes.set_xlabel('diff (ms)')
    axes.set_ylabel('fraction')

    
#     diff_counts = defaultdict(int)
#     slice_count = 0
#     
#     for forward_slices, backward_slices, call_start_index, call_end_index \
#             in dataset:
#         
#         gram_slices = gram_slices.numpy()
#         call_start_index = int(round(call_start_index.numpy()))
#         call_end_index = int(round(call_end_index.numpy()))
#         
#         # print(f'slices shape {gram_slices.shape}')
#             
#         if gram_slices.shape[0] != 0:
#             
#             scores = model.predict(gram_slices).flatten()
#             
#             index = np.argmax(scores) + settings.call_bound_index_offset
#             
#             diff = index - call_start_index
#             
#             print(np.max(score), index, call_start_index, diff)
#             
#             diff_counts[diff] += 1
#             slice_count += 1
#         
#     diffs = sorted(diff_counts.keys())
#     diff_sum = 0
#     diff_sum_2 = 0
#     for diff in diffs:
#         count = diff_counts[diff]
#         diff_sum += count * diff
#         diff_sum_2 += count * diff * diff
#         print(diff, count)
#     diff_mean = diff_sum / slice_count
#     diff_std = math.sqrt(diff_sum_2 / slice_count - diff_mean * diff_mean)
#         
#            
#     print(f'{slice_count} {diff_mean} {diff_std}')
#         for i, p in enumerate(predictions):
#             print(i, p)
    
    
def validate_annotator_old(model_name):
    
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        CLIP_TYPE, model_name)
    model = tf.keras.models.load_model(model_dir_path)
    
    model.summary()
    
    dataset = dataset_utils.create_training_dataset('Validation', TSEEP_SETTINGS).take(500)
    
    diff_counts = defaultdict(int)
    slice_count = 0
    
    for gram_slices, call_start_index, call_end_index, _ in dataset:
        
        gram_slices = gram_slices.numpy()
        call_start_index = int(round(call_start_index.numpy()))
        call_end_index = int(round(call_end_index.numpy()))
        
        # print(f'slices shape {gram_slices.shape}')
            
        if gram_slices.shape[0] != 0:
            
            predictions = model.predict(gram_slices).flatten()
            
            # TODO: Get offset from saved settings?
            prediction = np.argmax(predictions) + 9
            
            diff = prediction - call_start_index
            
            print(np.max(predictions), prediction, call_start_index, diff)
            
            diff_counts[diff] += 1
            slice_count += 1
        
    diffs = sorted(diff_counts.keys())
    diff_sum = 0
    diff_sum_2 = 0
    for diff in diffs:
        count = diff_counts[diff]
        diff_sum += count * diff
        diff_sum_2 += count * diff * diff
        print(diff, count)
    diff_mean = diff_sum / slice_count
    diff_std = math.sqrt(diff_sum_2 / slice_count - diff_mean * diff_mean)
        
           
    print(f'{slice_count} {diff_mean} {diff_std}')
#         for i, p in enumerate(predictions):
#             print(i, p)
        

def get_sliced_clip_gram_dataset(name):
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    
    utils = dataset_utils
    
    return utils.create_sliced_clip_spectrogram_dataset_from_waveform_files(
        dir_path, TSEEP_SETTINGS)
    

def extract_clip_waveform(
        waveform, clip_start_index, clip_end_index, call_start_index,
        call_end_index, clip_id):
    
    waveform = waveform[clip_start_index, clip_end_index]
    call_start_index -= clip_start_index
    call_end_index -= clip_start_index
    
    return waveform, call_start_index, call_end_index, clip_id


# def slice_gram(gram, call_start_index, call_end_index, _):
#     
#     slice_length = EXAMPLE_SHAPE[0]
#     gram_slices = tf.signal.frame(gram, slice_length, 1, axis=0)
#  
#     # Reshape gram slices for input into Keras CNN.
#     gram_slices = tf.expand_dims(gram_slices, 3)
#     
#     if BOUND_NAME == 'start':
#         bound_index = call_start_index
#     else:
#         bound_index = call_end_index
# 
#     return gram, gram_slices, bound_index


def plot_first_gram(dataset_name, model_name):
    
    dataset = get_dataset(dataset_name).take(1)
    
    # model_dir_path = MODEL_DIR_PATH / model_name
    # model = tf.keras.models.load_model(model_dir_path)
    
    for gram, bound_fraction in dataset:
        
        # grams = tf.expand_dims(gram, 0)
        # predictions = model.predict(grams)
        # prediction = predictions[0, 0]
        
        gram = np.flipud(gram[:, :, 0].numpy().T)
        plt.imshow(gram)
        
        spectrum_count = gram.shape[1]
        bound_index = bound_fraction * spectrum_count
        # prediction_index = prediction * spectrum_count
        plt.vlines(bound_index, 0, gram.shape[0], colors='r')
        
        plt.show()
        
    
def show_model_summary(model_name):
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        CLIP_TYPE, model_name)
    model = tf.keras.models.load_model(model_dir_path)
    model.summary()
    
    
def test_bincount():
    
    # Start with two-dimensional float tensor of spectra. First dimension
    # is time, second is frequency.
    x = tf.convert_to_tensor([
        [.9, 1, 2],
        [0, 2.1, 1],
        [0, 2, 1.2],
        [0, 0.1, 0]
    ])
    
    # Round values to nearest integer.
    x = tf.cast(tf.round(x), tf.int32)
    
    # Transpose tensor so first dimension is frequency.
    x = tf.transpose(x)
    
    print(x)
    
    def fn(x):
        counts = tf.math.bincount(x, minlength=3)
        return tf.cumsum(counts)
    
    counts = tf.map_fn(fn, x)
    
    print(counts)
    
    
def test_create_waveform_dataset_from_tensors():
    
    waveforms = [
        np.array([0, 16384]),
        np.array([0, 16384, 32768])]
    
    dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
    
    for waveform in dataset:
        print(waveform)
        
        
def test_create_waveform_dataset_from_tfrecord_files(name):
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    
    dataset = dataset_utils.create_waveform_dataset_from_tfrecord_files(
        dir_path)
    
    show_waveform_dataset_stats(dataset)
    
    
def show_waveform_dataset_stats(dataset):
    
    sample_rate = TSEEP_SETTINGS.waveform_sample_rate
    
    example_count = 10000
    dataset = dataset.take(example_count)
    
    min_start_time = 1000000
    max_start_time = 0
    min_end_time = 1000000
    max_end_time = 0
    min_duration = 1000000
    max_duration = 0
    
    start_time = time.time()
    
    for waveform, clip_start_index, clip_end_index, call_start_index, \
            call_end_index, clip_id in dataset:
        
        clip_start_index = clip_start_index.numpy()
        clip_end_index = clip_end_index.numpy()
        call_start_index = call_start_index.numpy()
        call_end_index = call_end_index.numpy()
        clip_id = clip_id.numpy()
        
        call_start_time = int(round(1000 * call_start_index / sample_rate))
        min_start_time = min(min_start_time, call_start_time)
        max_start_time = max(max_start_time, call_start_time)
        
        call_end_time = int(round(1000 * call_end_index / sample_rate))
        min_end_time = min(min_end_time, call_end_time)
        max_end_time = max(max_end_time, call_end_time)
        
        call_duration = call_end_time - call_start_time
        min_duration = min(min_duration, call_duration)
        max_duration = max(max_duration, call_duration)
        
#         print(
#             clip_id, len(waveform), clip_start_index, clip_end_index,
#             call_start_index, call_end_index, call_start_time, call_end_time,
#             call_duration)
        
    end_time = time.time()
    delta_time = end_time - start_time
    rate = example_count / delta_time
    print(
        f'Generated {example_count} examples in {delta_time} seconds, '
        f'a rate of {rate} examples per second.')
        
    print(f'call start time range ({min_start_time}, {max_start_time})')
    print(f'call end time range ({min_end_time}, {max_end_time})')
    print(f'call duration range ({min_duration}, {max_duration})')
    
    
def test_create_training_dataset(name):
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    
    dataset = dataset_utils.create_training_dataset(dir_path, TSEEP_SETTINGS)
    
    show_training_dataset_stats(dataset)
    
    
def show_training_dataset_stats(dataset):
    
    example_count = 10000
    dataset = dataset.take(example_count)
    
    start_time = time.time()
    
    positive_count = 0
    for gram, label in dataset:
        # print(f'gram {gram.shape} {label}')
        if label == 1:
            positive_count += 1
        
    end_time = time.time()
    delta_time = end_time - start_time
    rate = example_count / delta_time
    print(
        f'Generated {example_count} examples in {delta_time} seconds, '
        f'a rate of {rate} examples per second.')
    
    percent = 100 * positive_count / example_count 
    print(f'{positive_count} examples, or {percent} percent, were positives.')
    
    
def test_create_inference_dataset():
    
    waveform_durations = [.5, .6]
    waveforms = [_create_random_waveform(d) for d in waveform_durations]
    dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
    
    dataset = dataset_utils.create_inference_dataset(dataset, TSEEP_SETTINGS)
    
    for forward_slices, backward_slices in dataset:
        slice_count = forward_slices.shape[0]
        assert(backward_slices.shape[0] == slice_count)
        for i in range(slice_count):
            forward_slice = forward_slices[i]
            backward_slice = backward_slices[slice_count - 1 - i]
            _compare_tensors(forward_slice, backward_slice)

            
def _compare_tensors(x, y):
    
    """
    Checks that tensor x is the same as tensor y but with the first axis
    reversed.
    """
    
    assert(tf.reduce_all(x == tf.reverse(y, (0,))))
    

def _create_random_waveform(duration):
    length = int(round(duration * TSEEP_SETTINGS.waveform_sample_rate))
    return np.random.random_integers(-32768, 32767, length)


def test_create_preprocessed_waveform_dataset(name):
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    
    dataset = dataset_utils.create_waveform_dataset_from_waveform_files(
        dir_path)
    
    dataset = dataset_utils.create_preprocessed_waveform_dataset(
        dataset, dataset_utils.DATASET_MODE_TRAINING, TSEEP_SETTINGS)
    
    show_preprocessed_waveform_dataset_stats(dataset)
    
    
def show_preprocessed_waveform_dataset_stats(dataset):
    
    sample_rate = TSEEP_SETTINGS.waveform_sample_rate
    
    example_count = 100
    dataset = dataset.take(example_count)
    
    positive_count = 0
    
    start_time = time.time()
    
    for waveform, label, clip_id in dataset:
        
        label = label.numpy()
        clip_id = clip_id.numpy()
        
        print(label, len(waveform), clip_id)
        
        positive_count += label
        
#     for waveform, original_length, clip_start_index, slice_start_index, \
#             label, clip_id in dataset:
#         
#         original_length = original_length.numpy()
#         clip_start_index = clip_start_index.numpy()
#         slice_start_index = slice_start_index.numpy()
#         label = label.numpy()
#         clip_id = clip_id.numpy()
#         
#         length = len(waveform)
#         slice_end_index = slice_start_index + length
#         print(
#             label, original_length, clip_start_index, slice_start_index,
#             slice_end_index, length, clip_id)
#         
#         positive_count += label
               
    end_time = time.time()
    delta_time = end_time - start_time
    rate = example_count / delta_time
    print(
        f'Generated {example_count} examples in {delta_time} seconds, '
        f'a rate of {rate} examples per second.')
        
#         print(
#             clip_id, len(waveform), call_start_index, call_end_index,
#             call_start_time, call_end_time, call_duration)
        
    print(f'{positive_count} of {example_count} examples were positive.')
    
    
def test_create_spectrogram_dataset(name):
    
    dir_path = annotator_utils.get_dataset_dir_path(CLIP_TYPE, name)
    
    dataset = dataset_utils.create_spectrogram_dataset_from_waveform_files(
        dir_path, dataset_utils.DATASET_MODE_TRAINING, TSEEP_SETTINGS)
    
    show_spectrogram_dataset_stats(dataset)
    
    
if __name__ == '__main__':
    main()
