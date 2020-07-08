"""
Script that trains an NFC bounding interval annotator.

To use tensorboard during or after model training, open a terminal and say:

    conda activate vesper-dev-tf2
    tensorboard --logdir "/Users/Harold/Desktop/NFC/Data/Vesper ML/
        NFC Bounding Interval Annotator 1.0/Logs/<training log dir path>"
        
and then visit:

    127.0.0.1:6006
    
in Chrome.
"""


from collections import defaultdict
import math
import time

from matplotlib.backends.backend_pdf import PdfPages
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


TSEEP_SETTINGS = Settings(
    
    clip_type='Tseep',
    
    bound_type='Start',
    
    waveform_sample_rate=24000,
    
    # `True` if and only if the waveform time reversal data augmentation
    # is enabled. This augmentation reverses each waveform with
    # probability .5.
    waveform_time_reversal_data_augmentation_enabled=False,
    
    positive_example_probability=.5,
    positive_example_call_start_offset=.0275,
    
    waveform_slice_duration=.080,
    
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
    spectrogram_end_freq=10500,
    
    # The maximum spectrogram frequency shift for data augmentation,
    # in bins. Set this to zero to disable this augmentation.
    max_spectrogram_frequency_shift=2,
    
    # training settings
    training_batch_size=128,
    training_epoch_count=50,
    training_epoch_step_count=50,
    
    # validation settings
    validation_batch_size=1,
    validation_step_count=500,
    
    # validation plot settings
    max_validation_inlier_diff=20,
    
    # offset for converting inference value to spectrogram index
    call_bound_index_offset=10
    
)


def main():
    
    settings = TSEEP_SETTINGS
    
    train_and_validate_annotator(settings)
    
    # validate_annotator('2020-07-06_09.33.54')
    
    # show_model_summary('start_2020-06-10_12.13.39')
    
    # test_bincount()
    
    # test_create_waveform_dataset_from_tensors()
    
    # test_create_waveform_dataset_from_tfrecord_files('Training', settings)
    
    # test_create_training_dataset('Training', settings)
    
    # test_create_inference_dataset(settings)


def train_and_validate_annotator(settings):
    model_name = annotator_utils.create_model_name(settings)
    train_annotator(model_name, settings)
    validate_annotator(model_name)


def train_annotator(model_name, settings):
    
    s = settings
    
    training_dataset = get_dataset('Training', s).batch(s.training_batch_size)
    validation_dataset = \
        get_dataset('Validation', s).batch(s.validation_batch_size)
    
    input_shape = dataset_utils.get_spectrogram_slice_shape(settings)
    
    model = Sequential([
        
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        BatchNormalization(),
        MaxPooling2D((1, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),
 
        Conv2D(32, (3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D((1, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),

        Flatten(),
        
        # Dense(32, activation='relu'),
        # BatchNormalization(),
        
        Dense(32, activation='relu'),
        BatchNormalization(),
        
        Dense(1, activation='sigmoid')
        
    ])
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    model.summary()
    
    log_dir_path = annotator_utils.get_log_dir_path(model_name)
    callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir_path, histogram_freq=1)
     
    model.fit(
        training_dataset, epochs=s.training_epoch_count,
        steps_per_epoch=s.training_epoch_step_count, verbose=2,
        validation_data=validation_dataset,
        validation_steps=s.validation_step_count,
        callbacks=[callback])
     
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        model_name)
    model.save(model_dir_path)
    
    save_model_settings(settings, model_name)


def get_dataset(name, settings):
    dir_path = annotator_utils.get_dataset_dir_path(settings.clip_type, name)
    return dataset_utils.create_training_dataset(dir_path, settings)


def save_model_settings(settings, model_name):
    file_path = annotator_utils.get_model_settings_file_path(model_name)
    text = yaml_utils.dump(settings.__dict__, default_flow_style=False)
    file_path.write_text(text)


def validate_annotator(model_name):
    
    _, settings = annotator_utils.load_model_and_settings(model_name)
    
    dir_path = annotator_utils.get_dataset_dir_path(
        settings.clip_type, 'Validation')
    dataset = dataset_utils.create_validation_dataset(dir_path, settings)
    
    dataset = dataset.take(settings.validation_step_count)
    
    inferrer = Inferrer(model_name)
    
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

    _show_diff_counts('start', start_diff_counts, settings)
    _show_diff_counts('end', end_diff_counts, settings)
    
    _plot_diff_counts(model_name, start_diff_counts, end_diff_counts, settings)
    
    
def _get_diff(inferred_index, dataset_index, sample_rate):
    
    if inferred_index is None:
        return None
    
    else:
        sample_count = inferred_index - dataset_index
        return int(round(1000 * sample_count / sample_rate))


def _show_diff_counts(name, counts, settings):
    
    diffs = sorted(counts.keys())
    
    # Calculate error mean and standard deviation, excluding outliers.
    diff_sum = 0
    diff_sum_2 = 0
    inlier_count = 0
    outlier_count = 0
    for diff in diffs:
        count = counts[diff]
        if diff <= settings.max_validation_inlier_diff:
            diff_sum += count * diff
            diff_sum_2 += count * diff * diff
            inlier_count += count
        else:
            outlier_count += count
    diff_mean = diff_sum / inlier_count
    diff_std = math.sqrt(diff_sum_2 / inlier_count - diff_mean * diff_mean)
    
    print(f'{name} {inlier_count} {diff_mean} {diff_std} {outlier_count}')
    
    
def _plot_diff_counts(
        model_name, start_diff_counts, end_diff_counts, settings):

    file_path = annotator_utils.get_validation_plot_file_path(model_name)
    
    with PdfPages(file_path) as pdf:
    
        _, (start_axes, end_axes) = plt.subplots(2)
        
        title = f'{model_name} Call Start Errors'
        _plot_diff_counts_aux(start_axes, title, start_diff_counts, settings)
        
        title = f'{model_name} Call End Errors'
        _plot_diff_counts_aux(end_axes, title, end_diff_counts, settings)
        
        plt.tight_layout()
        
        pdf.savefig()
        
        plt.close()
    
    
def _plot_diff_counts_aux(axes, title, counts, settings):
    
    limit = settings.max_validation_inlier_diff
    x = np.arange(-limit, limit + 1)
    
    total_count = sum(counts.values())
    y = np.array([counts[d] for d in x]) / total_count
    
    axes.bar(x, y)
    axes.set_title(title)
    axes.set_xlabel('diff (ms)')
    axes.set_ylabel('fraction')

    
def show_model_summary(model_name):
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        model_name)
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
    
    print('rounded and transposed spectrogram:')
    print(x)
    
    def fn(x):
        counts = tf.math.bincount(x, minlength=3)
        return tf.cumsum(counts)
    
    counts = tf.map_fn(fn, x)
    
    print()
    print('cumulative sums of rounded bin values:')
    print(counts)
    
    
def test_create_waveform_dataset_from_tensors():
    
    waveforms = [
        np.array([0, 16384]),
        np.array([0, 16384, 32768])]
    
    dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
    
    for waveform in dataset:
        print(waveform)
        
        
def test_create_waveform_dataset_from_tfrecord_files(dataset_name, settings):
    
    dir_path = annotator_utils.get_dataset_dir_path(
        settings.clip_type, dataset_name)
    
    dataset = dataset_utils.create_waveform_dataset_from_tfrecord_files(
        dir_path)
    
    show_waveform_dataset_stats(dataset, settings.waveform_sample_rate)
    
    
def show_waveform_dataset_stats(dataset, sample_rate):
    
    example_count = 10000
    dataset = dataset.take(example_count)
    
    min_start_time = 1000000
    max_start_time = 0
    min_end_time = 1000000
    max_end_time = 0
    min_duration = 1000000
    max_duration = 0
    
    start_time = time.time()
    
    for _, clip_start_index, clip_end_index, call_start_index, \
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
    
    
def test_create_training_dataset(dataset_name, settings):
    
    dir_path = annotator_utils.get_dataset_dir_path(
        settings.clip_type, dataset_name)
    
    dataset = dataset_utils.create_training_dataset(dir_path, settings)
    
    show_training_dataset_stats(dataset)
    
    
def show_training_dataset_stats(dataset):
    
    example_count = 10000
    dataset = dataset.take(example_count)
    
    start_time = time.time()
    
    positive_count = 0
    for _, label in dataset:
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
    
    
def test_create_inference_dataset(settings):
    
    waveform_durations = [.5, .6]
    sample_rate = settings.waveform_sample_rate
    waveforms = [
        _create_random_waveform(d, sample_rate)
        for d in waveform_durations
    ]
    dataset = dataset_utils.create_waveform_dataset_from_tensors(waveforms)
    
    dataset = dataset_utils.create_inference_dataset(dataset, settings)
    
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
    

def _create_random_waveform(duration, sample_rate):
    length = int(round(duration * sample_rate))
    return np.random.randint(-32768, 32768, length)
    
    
if __name__ == '__main__':
    main()
