"""Utility functions pertaining to classifiers."""


from pathlib import Path


_CLASSIFIER_DIR_NAME_FORMAT = '{} Classifier'
KERAS_MODEL_FILE_NAME = 'Keras Model.h5'
SETTINGS_FILE_NAME = 'Settings.yaml'


def get_classifier_dir_path(clip_type):
    package_path = Path(__file__).parent
    dir_name = _CLASSIFIER_DIR_NAME_FORMAT.format(clip_type)
    return package_path.joinpath(dir_name)


def get_keras_model_file_path(clip_type):
    dir_path = get_classifier_dir_path(clip_type)
    return dir_path.joinpath(KERAS_MODEL_FILE_NAME)
 
 
def get_settings_file_path(clip_type):
    dir_path = get_classifier_dir_path(clip_type)
    return dir_path.joinpath(SETTINGS_FILE_NAME)
