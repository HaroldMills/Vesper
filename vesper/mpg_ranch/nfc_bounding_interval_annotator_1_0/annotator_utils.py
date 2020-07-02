from pathlib import Path


_ML_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/Vesper ML/'
    'NFC Bounding Interval Annotator 1.0/')

_MODEL_DIR_PATH = _ML_DIR_PATH / 'Models'
_TENSORFLOW_SAVED_MODEL_DIR_NAME = 'TensorFlow SavedModel'
_MODEL_SETTINGS_FILE_NAME = 'Model Settings.yaml'


def get_dataset_dir_path(clip_type, dataset_name):
    return _ML_DIR_PATH / 'Datasets' / clip_type / dataset_name
    
    
def get_log_dir_path(clip_type, model_name):
    return _ML_DIR_PATH / 'Logs' / clip_type / model_name


def get_model_dir_path(clip_type, model_name):
    return _MODEL_DIR_PATH / clip_type / model_name
    
    
def get_tensorflow_saved_model_dir_path(clip_type, model_name):
    model_dir_path = get_model_dir_path(clip_type, model_name)
    return model_dir_path / _TENSORFLOW_SAVED_MODEL_DIR_NAME


def get_model_settings_file_path(clip_type, model_name):
    model_dir_path = get_model_dir_path(clip_type, model_name)
    return model_dir_path / _MODEL_SETTINGS_FILE_NAME
