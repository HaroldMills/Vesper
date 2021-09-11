from pathlib import Path
import datetime
import logging

import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.yaml_utils as yaml_utils 


_ML_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/NOGO Coarse Classifier 0.0')

_MODEL_DIR_PATH = _ML_DIR_PATH / 'Models'
_EPOCH_DIR_NAME_FORMAT = 'Epoch {}'
_TENSORFLOW_SAVED_MODEL_DIR_NAME = 'TensorFlow SavedModel'
_TRAINING_SETTINGS_FILE_NAME = 'Training Settings.yaml'


def get_dataset_dir_path(clip_type, dataset_name):
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
