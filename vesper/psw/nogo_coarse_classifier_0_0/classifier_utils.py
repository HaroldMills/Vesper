from pathlib import Path
import datetime
import logging

import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.yaml_utils as yaml_utils 


_TRAINING_DATA_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NOGO Coarse Classifier 0.0')

_MODEL_DIR_PATH = _TRAINING_DATA_DIR_PATH / 'Models'
_EPOCH_DIR_NAME_FORMAT = 'Epoch {}'
_TENSORFLOW_SAVED_MODEL_DIR_NAME = 'TensorFlow SavedModel'
_KERAS_MODEL_FILE_NAME = 'Keras Model.h5'
_TRAINING_SETTINGS_FILE_NAME = 'Training Settings.yaml'

_INFERENCE_DATA_DIR_PATH = Path(__file__).parent / 'data'

_INFERENCE_SETTING_CHANGES = Settings(
    waveform_slice_min_non_call_slice_start_time=0,
    waveform_slice_max_non_call_slice_start_time=0,
    waveform_amplitude_scaling_data_augmentation_enabled=False,
    max_spectrogram_frequency_shift=0,
)
"""Changes to training settings for inference."""



def get_dataset_dir_path(dataset_name):
    return _TRAINING_DATA_DIR_PATH / 'Datasets' / dataset_name
    
    
def create_training_name(settings):
    start_time = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    return f'{start_time}'


def get_training_start_time(training_name):
    return training_name


def get_training_log_dir_path(training_name):
    return _TRAINING_DATA_DIR_PATH / 'Logs' / training_name


def get_training_model_dir_path(training_name):
    return _MODEL_DIR_PATH / training_name
    
    
def get_training_epoch_model_dir_path(training_name, epoch_num):
    training_model_dir_path = get_training_model_dir_path(training_name)
    epoch_dir_name = _EPOCH_DIR_NAME_FORMAT.format(epoch_num)
    return training_model_dir_path / epoch_dir_name


def get_training_tensorflow_model_dir_path(training_name, epoch_num):
    model_dir_path = \
        get_training_epoch_model_dir_path(training_name, epoch_num)
    return model_dir_path / _TENSORFLOW_SAVED_MODEL_DIR_NAME


def get_training_keras_model_file_path(training_name, epoch_num):
    model_dir_path = \
        get_training_epoch_model_dir_path(training_name, epoch_num)
    return model_dir_path / _KERAS_MODEL_FILE_NAME


def load_training_model(training_name, epoch_num):
    file_path = get_training_keras_model_file_path(training_name, epoch_num)
    return _load_model(file_path)


def _load_model(file_path):
    logging.info(f'Loading classifier model from "{file_path}"...')
    return tf.keras.models.load_model(file_path)


def load_inference_model():
    file_path = _INFERENCE_DATA_DIR_PATH / _KERAS_MODEL_FILE_NAME
    return _load_model(file_path)
    
    
def get_training_settings_file_path(training_name):
    model_dir_path = get_training_model_dir_path(training_name)
    return model_dir_path / _TRAINING_SETTINGS_FILE_NAME


def save_training_settings(settings, training_name):
    file_path = get_training_settings_file_path(training_name)
    text = yaml_utils.dump(settings.__dict__, default_flow_style=False)
    file_path.write_text(text)


def load_training_settings(training_name):
    file_path = get_training_settings_file_path(training_name)
    return _load_settings(file_path)


def _load_settings(file_path):
    logging.info(f'Loading classifier settings from "{file_path}"...')
    text = file_path.read_text()
    dict_ = yaml_utils.load(text)
    return Settings.create_from_dict(dict_)


def load_inference_settings():
    file_path = _INFERENCE_DATA_DIR_PATH / _TRAINING_SETTINGS_FILE_NAME
    training_settings = _load_settings(file_path)
    return get_inference_settings(training_settings)


def get_inference_settings(training_settings):
    return Settings(training_settings, _INFERENCE_SETTING_CHANGES)
