from pathlib import Path
import datetime
import time

from tensorflow.keras.layers import (
    BatchNormalization, Conv2D, Dense, Flatten, MaxPooling2D)
from tensorflow.keras.models import Sequential
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf

from vesper.util.settings import Settings
import vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.dataset_utils \
    as dataset_utils


CALL_TYPE = 'Tseep'
BOUND_NAME = 'start'

ML_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'NFC Bounding Interval Annotator 1.0/')

DATASET_DIR_PATH = ML_DIR_PATH / 'Datasets' / CALL_TYPE
MODEL_DIR_PATH = ML_DIR_PATH / 'Models' / CALL_TYPE
LOG_DIR_PATH = ML_DIR_PATH / 'Logs' / CALL_TYPE

EXAMPLE_SHAPE = (319, 33, 1)


'''
Tseep:
150 ms intro
250 ms start window
250 ms max duration
150 ms outro
800 ms total
Clip to yield 320 spectra with 5 ms window size and 2.5 ms hop size.

Preprocessing:

* Given samples and start index, clip samples to place start index uniformly
  within start window.

* Reverse time with probability .5.

* Offset spectrogram to place some power statistic (a percentile, perhaps?)
  uniformly within some range, or use some sort of normalization like PCEN?
'''


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
    waveform_time_reversal_data_augmentation_enabled=False,
    
    waveform_slice_duration=.8,
    
    # Waveform slice time window for call start time shift data
    # augmentation. When this augmentation is enabled (always during
    # training and during evaluation if evaluation data augmentation
    # is enabled), waveforms are sliced to distribute call start times
    # uniformly within a window.
    call_start_window_start_time=.15,
    call_start_window_duration=.25,
    
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
    
)


'''
* Plot of predictions of trained network on validation spectrograms.
* Don't augment validation data?
'''


def main():
    
    # test_bincount()
    
    # test_create_waveform_dataset('Training')
    
    # test_create_preprocessed_waveform_dataset('Training')
    
    # test_create_spectrogram_dataset('Training')
    
    train_and_validate_annotator()
    
    # plot_first_gram('Validation', 'end_2020-06-10_17.27.22')
    # plot_first_gram('Validation', 'start_2020-06-10_12.13.39')
    
    # show_model_summary('start_2020-06-10_12.13.39')
    

def train_and_validate_annotator():
    run_name = get_run_name()
    train_annotator(run_name)
    validate_annotator(run_name)


def get_run_name():
    start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    return f'{BOUND_NAME}_{start_time}'


'''
    Model that performs best so far:
    
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=EXAMPLE_SHAPE),
        # BatchNormalization(),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        # BatchNormalization(),
        MaxPooling2D((2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        # BatchNormalization(),
        Flatten(),
        # Dense(32, activation='relu'),
        # BatchNormalization(),
        Dense(64, activation='relu'),
        # BatchNormalization(),
        Dense(1)
    ])
    
    
    Switching pooling parameter to (1, 2) to try to improve temporal
    resolution actually increases MSE. I'm not sure why. Network has
    roughly five times the number of weights, though. The first
    dense layer accounts for most of the network parameters.

'''


def train_annotator(run_name):
    
    training_dataset = get_dataset('Training').batch(128)
    validation_dataset = get_dataset('Validation').batch(1)
    
    model = Sequential([
        
        Conv2D(32, (3, 3), activation='relu', input_shape=EXAMPLE_SHAPE),
        # BatchNormalization(),
        MaxPooling2D((2, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),
 
        Conv2D(64, (3, 3), activation='relu'),
        # BatchNormalization(),
        MaxPooling2D((2, 2)),
        
        # Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),

        Conv2D(64, (3, 3), activation='relu'),
        # BatchNormalization(),
        
        Conv2D(32, (1, 1), activation='relu'),
        # BatchNormalization(),
        
        Flatten(),
        
        # Dense(32, activation='relu'),
        # BatchNormalization(),
        
        Dense(64, activation='relu'),
        # BatchNormalization(),
        
        Dense(1)
        
    ])
    
    loss_fn = tf.keras.losses.MeanSquaredError()
    
    model.compile(optimizer='adam', loss=loss_fn)
    
    model.summary()
    
    log_dir_path = LOG_DIR_PATH / run_name
    callback = tf.keras.callbacks.TensorBoard(
        log_dir=log_dir_path, histogram_freq=1)
     
    model.fit(
        training_dataset, epochs=100, steps_per_epoch=100, verbose=2,
        validation_data=validation_dataset, validation_steps=500,
        callbacks=[callback])
     
    model_dir_path = MODEL_DIR_PATH / run_name
    model.save(model_dir_path)


def get_dataset(name):
    
    dir_path = DATASET_DIR_PATH / name
    
    dataset = dataset_utils.create_spectrogram_dataset_from_waveform_files(
        dir_path, dataset_utils.DATASET_MODE_TRAINING, TSEEP_SETTINGS)
    
    return dataset.map(diddle_example)
    

def diddle_example(gram, call_start_index, call_end_index, _):
    
    # Reshape gram for input into Keras CNN.
    gram = tf.expand_dims(gram, 2)
        
    spectrum_count = EXAMPLE_SHAPE[0]
    
    if BOUND_NAME == 'start':
        bound_fraction = call_start_index / spectrum_count
    else:
        bound_fraction = call_end_index / spectrum_count
    
    return gram, bound_fraction


def validate_annotator(run_name):
    
    model_dir_path = MODEL_DIR_PATH / run_name
    model = tf.keras.models.load_model(model_dir_path)
    
    model.summary()
    
    dataset = get_dataset('Validation').take(10)
    
    for gram, bound_fraction in dataset:
        
        grams = tf.expand_dims(gram, 0)
        predictions = model.predict(grams)
        
        print(predictions, bound_fraction.numpy())


def plot_first_gram(dataset_name, run_name):
    
    dataset = get_dataset(dataset_name).take(1)
    
    # model_dir_path = MODEL_DIR_PATH / run_name
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
        
    
def show_model_summary(run_name):
    model_dir_path = MODEL_DIR_PATH / run_name
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
    
    
def test_create_waveform_dataset(name):
    
    dir_path = DATASET_DIR_PATH / name
    
    dataset = dataset_utils.create_waveform_dataset_from_waveform_files(
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
    
    for waveform, call_start_index, call_end_index, clip_id in dataset:
        
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
        
    end_time = time.time()
    delta_time = end_time - start_time
    rate = example_count / delta_time
    print(
        f'Generated {example_count} examples in {delta_time} seconds, '
        f'a rate of {rate} examples per second.')
        
#         print(
#             clip_id, len(waveform), call_start_index, call_end_index,
#             call_start_time, call_end_time, call_duration)
        
    print(f'call start time range ({min_start_time}, {max_start_time})')
    print(f'call end time range ({min_end_time}, {max_end_time})')
    print(f'call duration range ({min_duration}, {max_duration})')
    
    
def test_create_preprocessed_waveform_dataset(name):
    
    dir_path = DATASET_DIR_PATH / name
    
    dataset = dataset_utils.create_waveform_dataset_from_waveform_files(
        dir_path)
    
    dataset = dataset_utils.create_preprocessed_waveform_dataset(
        dataset, dataset_utils.DATASET_MODE_TRAINING, TSEEP_SETTINGS)
    
    show_waveform_dataset_stats(dataset)
    
    
def test_create_spectrogram_dataset(name):
    
    dir_path = DATASET_DIR_PATH / name
    
    dataset = dataset_utils.create_spectrogram_dataset_from_waveform_files(
        dir_path, dataset_utils.DATASET_MODE_TRAINING, TSEEP_SETTINGS)
    
    show_spectrogram_dataset_stats(dataset)
    
    
def show_spectrogram_dataset_stats(dataset):
    
    example_count = 10
    dataset = dataset.take(example_count)
    
    start_time = time.time()
    
    for gram, call_start_index, call_end_index, _ in dataset:
        spectrum_count = gram.shape[0]
        call_start_fraction = call_start_index / spectrum_count
        call_end_fraction = call_end_index / spectrum_count
        print(f'gram {gram.shape} {call_start_fraction} {call_end_fraction}')
        
    end_time = time.time()
    delta_time = end_time - start_time
    rate = example_count / delta_time
    print(
        f'Generated {example_count} examples in {delta_time} seconds, '
        f'a rate of {rate} examples per second.')
    
    
if __name__ == '__main__':
    main()
