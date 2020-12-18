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
# from tensorflow.keras.layers import Dropout
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
    
    positive_example_probability=.5,
    positive_example_call_start_offset=.025,
    
    waveform_slice_duration=.080,
    
    # `True` if and only if the waveform amplitude scaling data
    # augmentation is enabled. This augmentation scales each waveform
    # randomly to distribute the waveform log RMS amplitudes uniformly
    # within a roughly 48 dB window.
    waveform_amplitude_scaling_data_augmentation_enabled=False,
    
    # spectrogram settings
    spectrogram_window_size=.005,
    spectrogram_hop_size=20,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=4000,
    spectrogram_end_freq=10500,
    
    # The maximum spectrogram frequency shift for data augmentation,
    # in bins. Set this to zero to disable this augmentation.
    max_spectrogram_frequency_shift=2,
    
    spectrogram_background_normalization_percentile_rank=30,
    
    # training settings
    training_batch_size=128,
    training_epoch_step_count=100,  # epoch size is batch size times step count
    training_epoch_count=30,
    model_save_period=5,            # epochs
    dropout_rate=.25,
    
    # validation settings
    validation_batch_size=1,
    validation_step_count=1000,
    
    # evaluation plot settings
    max_evaluation_inlier_diff=20,
    
    # offsets for converting inference value to spectrogram index
    call_start_index_offset=23,
    call_end_index_offset=22,
    
)


def main():
    
    settings = TSEEP_SETTINGS
    
    train_annotator(settings)
    
    # evaluate_annotator('2020-07-06_09.33.54')
    
    # show_model_summary('start_2020-06-10_12.13.39', 20)
    
    # test_get_spectrogram_percentiles()
    
    # test_create_waveform_dataset_from_tensors()
    
    # test_create_waveform_dataset_from_tfrecord_files('Training', settings)
    
    # test_create_training_dataset('Training', settings)
    
    # test_create_inference_dataset(settings)
    
    # show_dataset_sizes(settings)


def train_annotator(settings):
    
    s = settings
    
    training_name = annotator_utils.create_training_name(s)
    
    training_dataset = get_dataset('Training', s).batch(s.training_batch_size)
    validation_dataset = \
        get_dataset('Validation', s).batch(s.validation_batch_size)
    
    input_shape = dataset_utils.get_spectrogram_slice_shape(settings)
    
    model = Sequential([
        
        Conv2D(32, (3, 3), activation='relu', input_shape=input_shape),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        MaxPooling2D((1, 2)),
        
        # Conv2D(16, (1, 1), activation='relu'),
        # BatchNormalization(),
 
        Conv2D(32, (3, 3), activation='relu'),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        MaxPooling2D((1, 2)),
        
        # Conv2D(16, (1, 1), activation='relu'),
        # BatchNormalization(),

        Flatten(),
        
        # Dense(32, activation='relu'),
        # BatchNormalization(),
        
        Dense(32, activation='relu'),
        # Dropout(s.dropout_rate),
        BatchNormalization(),
        
        Dense(1, activation='sigmoid')
        
    ])
    
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy'])
    
    model.summary()
    
    log_dir_path = annotator_utils.get_training_log_dir_path(training_name)
    tensorboard_callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir_path, histogram_freq=1)
    
    model_save_callback = ModelSaveCallback(training_name, settings)
     
    model.fit(
        training_dataset, epochs=s.training_epoch_count,
        steps_per_epoch=s.training_epoch_step_count, verbose=2,
        validation_data=validation_dataset,
        validation_steps=s.validation_step_count,
        callbacks=[tensorboard_callback, model_save_callback])
     

class ModelSaveCallback(tf.keras.callbacks.Callback):
    
    
    def __init__(self, training_name, settings):
        self._training_name = training_name
        self._settings = settings
        
        
    def on_epoch_end(self, epoch, logs=None):
        
        epoch_num = epoch + 1
        
        if epoch_num % self._settings.model_save_period == 0:
            
            model_dir_path = \
                annotator_utils.get_tensorflow_saved_model_dir_path(
                    self._training_name, epoch_num)
                
            self.model.save(model_dir_path)
            
            save_training_settings(self._settings, self._training_name)
            
            print(f'Saved model at end of epoch {epoch_num}.')
            
            print('Evaluating model...')
            evaluate_annotator(self._training_name, epoch_num)

        
def get_dataset(name, settings):
    dir_path = annotator_utils.get_dataset_dir_path(settings.clip_type, name)
    return dataset_utils.create_training_dataset(dir_path, settings)


def save_training_settings(settings, training_name):
    file_path = annotator_utils.get_training_settings_file_path(training_name)
    text = yaml_utils.dump(settings.__dict__, default_flow_style=False)
    file_path.write_text(text)


def evaluate_annotator(training_name, epoch_num):
    
    _, settings = annotator_utils.load_model_and_settings(
        training_name, epoch_num)
    
    dir_path = annotator_utils.get_dataset_dir_path(
        settings.clip_type, 'Validation')
    dataset = dataset_utils.create_validation_dataset(dir_path, settings)
    
    dataset = dataset.take(settings.validation_step_count)
    
    inferrer = Inferrer((training_name, epoch_num))
    
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

    _show_diff_counts('Start', start_diff_counts, settings)
    _show_diff_counts('End', end_diff_counts, settings)
    
    _plot_diff_counts(
        training_name, epoch_num, start_diff_counts, end_diff_counts, settings)
    
    
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
        if diff <= settings.max_evaluation_inlier_diff:
            diff_sum += count * diff
            diff_sum_2 += count * diff * diff
            inlier_count += count
        else:
            outlier_count += count
    diff_mean = diff_sum / inlier_count
    diff_std = math.sqrt(diff_sum_2 / inlier_count - diff_mean * diff_mean)
    
    print(f'{name} {inlier_count} {diff_mean} {diff_std} {outlier_count}')
    
    
def _plot_diff_counts(
        training_name, epoch_num, start_diff_counts, end_diff_counts,
        settings):

    file_path = annotator_utils.get_evaluation_plot_file_path(
        training_name, epoch_num)
    
    with PdfPages(file_path) as pdf:
    
        _, (start_axes, end_axes) = plt.subplots(2)
        
        title = f'{training_name} Epoch {epoch_num} Call Start Errors'
        _plot_diff_counts_aux(start_axes, title, start_diff_counts, settings)
        
        title = f'{training_name} Epoch {epoch_num} Call End Errors'
        _plot_diff_counts_aux(end_axes, title, end_diff_counts, settings)
        
        plt.tight_layout()
        
        pdf.savefig()
        
        plt.close()
    
    
def _plot_diff_counts_aux(axes, title, counts, settings):
    
    limit = settings.max_evaluation_inlier_diff
    x = np.arange(-limit, limit + 1)
    
    total_count = sum(counts.values())
    y = np.array([counts[d] for d in x]) / total_count
    
    axes.bar(x, y)
    axes.set_title(title)
    axes.set_xlabel('diff (ms)')
    axes.set_ylabel('fraction')

    
def show_model_summary(training_name, epoch_num):
    model_dir_path = annotator_utils.get_tensorflow_saved_model_dir_path(
        training_name, epoch_num)
    model = tf.keras.models.load_model(model_dir_path)
    model.summary()
    
    
def test_get_spectrogram_percentiles():
    
    # For convenience of specification, here first dimension is frequency,
    # second is time. This tensor is transposed below, though, preceding
    # the call to `_get_spectrogram_percentiles`.
    gram = tf.constant([
        [1.1, 0, 0, 89.9],      # 0, 0, 1, 90
        [80, 60, 40, 20],       # 20, 40, 60, 80
        [40, 80, 130, -10]      # 0, 40, 80, 120
    ])
    
    print('gram:')
    print(gram)
    
    # Transpose gram so it's a sequence of spectra (i.e. so that first
    # dimension is time and second is frequency), as expected by
    # `_get_spectrogram_percentiles`.
    gram = tf.transpose(gram)
    
    ranks = tf.constant([25, 50, 75, 100])
    
    percentiles = dataset_utils._get_spectrogram_percentiles(gram, ranks)
    
    print('gram percentiles:')
    print(percentiles)
    
    
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
    
    
def show_dataset_sizes(settings):
    
    from tensorflow.data import TFRecordDataset
    
    for dataset_name in ('Training', 'Validation'):
        
        total_size = 0
        
        print(f'Sizes of files in dataset "{dataset_name}":')
        
        dir_path = annotator_utils.get_dataset_dir_path(
            settings.clip_type, dataset_name)
        
        file_paths = sorted(dir_path.glob('*.tfrecords'))
        
        for file_path in file_paths:
            dataset = TFRecordDataset([str(file_path)])
            size = 0
            for _ in dataset:
                size += 1
            print(f'    {file_path.name}: {size}')
            total_size += size
        
        print(f'Total size of dataset "{dataset_name}": {total_size}')


if __name__ == '__main__':
    main()
