from pathlib import Path
import datetime
import logging

import tensorflow as tf

from vesper.util.settings import Settings
import vesper.util.yaml_utils as yaml_utils 


_ML_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'NFC Bounding Interval Annotator 1.0/')

_MODEL_DIR_PATH = _ML_DIR_PATH / 'Models'
_TENSORFLOW_SAVED_MODEL_DIR_NAME = 'TensorFlow SavedModel'
_MODEL_SETTINGS_FILE_NAME = 'Model Settings.yaml'
_MODEL_VALIDATION_PLOT_FILE_NAME_FORMAT = '{}.pdf'


def get_dataset_dir_path(clip_type, dataset_name):
    return _ML_DIR_PATH / 'Datasets' / clip_type / dataset_name
    
    
def create_model_name(settings):
    clip_type = settings.clip_type
    now = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
    return f'{clip_type}_{now}'


def get_model_clip_type(model_name):
    return model_name.split('_')[0]


def get_log_dir_path(model_name):
    clip_type = get_model_clip_type(model_name)
    return _ML_DIR_PATH / 'Logs' / clip_type / model_name


def get_model_dir_path(model_name):
    clip_type = get_model_clip_type(model_name)
    return _MODEL_DIR_PATH / clip_type / model_name
    
    
def get_tensorflow_saved_model_dir_path(model_name):
    model_dir_path = get_model_dir_path(model_name)
    return model_dir_path / _TENSORFLOW_SAVED_MODEL_DIR_NAME


def get_model_settings_file_path(model_name):
    model_dir_path = get_model_dir_path(model_name)
    return model_dir_path / _MODEL_SETTINGS_FILE_NAME


def get_validation_plot_file_path(model_name):
    model_dir_path = get_model_dir_path(model_name)
    file_name = _MODEL_VALIDATION_PLOT_FILE_NAME_FORMAT.format(model_name)
    return model_dir_path / file_name
    
    
def load_model_and_settings(model_name):
    model = load_model(model_name)
    settings = load_model_settings(model_name)
    return model, settings


def load_model(model_name):
    dir_path = get_tensorflow_saved_model_dir_path(model_name)
    logging.info(f'Loading annotator model from "{dir_path}"...')
    return tf.keras.models.load_model(dir_path)


def load_model_settings(model_name):
    file_path = get_model_settings_file_path(model_name)
    logging.info(f'Loading annotator settings from "{file_path}"...')
    text = file_path.read_text()
    dict_ = yaml_utils.load(text)
    return Settings.create_from_dict(dict_)
