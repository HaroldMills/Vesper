from pathlib import Path
import datetime
import logging

import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.yaml_utils as yaml_utils 


TRAINING_SETTINGS = Settings(
    
    waveform_sample_rate=48000,
    
    # Offset from start of example call waveform of start of call, in seconds.
    waveform_call_start_time=.2,
    
    # Call start time settings. During training, example call waveforms
    # are sliced so that call start times are uniformly distributed in
    # the interval from `waveform_slice_min_call_start_time` to
    # `waveform_slice_max_call_start_time`.
    waveform_slice_min_call_start_time=.000,
    waveform_slice_max_call_start_time=.200,
    
    # Non-call slice start time settings. During training, example non-call
    # waveforms are sliced with start times uniformly distributed in
    # the interval from `waveform_slice_min_non_call_slice_start_time` to
    # `waveform_slice_max_non_call_slice_start_time`.
    waveform_slice_min_non_call_slice_start_time=.000,
    waveform_slice_max_non_call_slice_start_time=.200,
    
    waveform_slice_duration=.400,
    
    # `True` if and only if the waveform amplitude scaling data
    # augmentation is enabled. This augmentation scales each waveform
    # randomly to distribute the waveform log RMS amplitudes uniformly
    # within a roughly 48 dB window.
    waveform_amplitude_scaling_data_augmentation_enabled=True,
    
    # spectrogram settings
    spectrogram_window_size=.020,
    spectrogram_hop_size=50,
    spectrogram_log_epsilon=1e-10,
    
    # spectrogram frequency axis slicing settings
    spectrogram_start_freq=1000,
    spectrogram_end_freq=5000,
    
    # The maximum spectrogram frequency shift for data augmentation,
    # in bins. Set this to zero to disable this augmentation.
    max_spectrogram_frequency_shift=2,
    
    # spectrogram_background_normalization_percentile_rank=40,
    
    # training settings
    training_batch_size=128,
    training_epoch_step_count=32,  # epoch size is batch size times step count
    training_epoch_count=50,
    model_save_period=5,           # epochs
    dropout_rate=.3,
    
    # validation settings
    validation_batch_size=1,
    validation_step_count=1000,
    
)


EVALUATION_SETTINGS = Settings(
    TRAINING_SETTINGS,
    waveform_slice_min_non_call_slice_start_time=0,
    waveform_slice_max_non_call_slice_start_time=0,
    waveform_amplitude_scaling_data_augmentation_enabled=False,
    max_spectrogram_frequency_shift=0,
)


_ML_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NOGO Coarse Classifier 0.0')

_MODEL_DIR_PATH = _ML_DIR_PATH / 'Models'
_EPOCH_DIR_NAME_FORMAT = 'Epoch {}'
_TENSORFLOW_SAVED_MODEL_DIR_NAME = 'TensorFlow SavedModel'
_KERAS_MODEL_FILE_NAME = 'Keras Model.h5'
_TRAINING_SETTINGS_FILE_NAME = 'Training Settings.yaml'


def get_dataset_dir_path(dataset_name):
    return _ML_DIR_PATH / 'Datasets' / dataset_name
    
    
def create_training_name(settings):
    start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    return f'{start_time}'


def get_training_start_time(training_name):
    return training_name


def get_training_log_dir_path(training_name):
    return _ML_DIR_PATH / 'Logs' / training_name


def get_training_model_dir_path(training_name):
    return _MODEL_DIR_PATH / training_name
    
    
def get_epoch_model_dir_path(training_name, epoch_num):
    training_model_dir_path = get_training_model_dir_path(training_name)
    epoch_dir_name = _EPOCH_DIR_NAME_FORMAT.format(epoch_num)
    return training_model_dir_path / epoch_dir_name


def get_tensorflow_saved_model_dir_path(training_name, epoch_num):
    model_dir_path = get_epoch_model_dir_path(training_name, epoch_num)
    return model_dir_path / _TENSORFLOW_SAVED_MODEL_DIR_NAME


def get_keras_model_file_path(training_name, epoch_num):
    model_dir_path = get_epoch_model_dir_path(training_name, epoch_num)
    return model_dir_path / _KERAS_MODEL_FILE_NAME


def get_training_settings_file_path(training_name):
    model_dir_path = get_training_model_dir_path(training_name)
    return model_dir_path / _TRAINING_SETTINGS_FILE_NAME


def load_model_and_settings(training_name, epoch_num):
    model = load_model(training_name, epoch_num)
    settings = load_training_settings(training_name)
    return model, settings


def load_model(training_name, epoch_num):
    dir_path = get_tensorflow_saved_model_dir_path(training_name, epoch_num)
    logging.info(f'Loading annotator model from "{dir_path}"...')
    return tf.keras.models.load_model(str(dir_path))


def load_training_settings(training_name):
    file_path = get_training_settings_file_path(training_name)
    logging.info(f'Loading annotator settings from "{file_path}"...')
    text = file_path.read_text()
    dict_ = yaml_utils.load(text)
    return Settings.create_from_dict(dict_)
