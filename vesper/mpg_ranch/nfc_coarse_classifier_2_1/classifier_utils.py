"""Utility functions pertaining to classifiers."""


from pathlib import Path


_DATA_DIR_NAME = '{} Classifier'
_MODEL_FILE_NAME = 'Keras Model.h5'
_SETTINGS_FILE_NAME = 'Settings.yaml'


def get_data_dir_path(clip_type):
    package_path = Path(__file__).parent
    dir_name = _DATA_DIR_NAME.format(clip_type)
    return package_path.joinpath(dir_name)


def get_model_file_path(clip_type):
    dir_path = get_data_dir_path(clip_type)
    return dir_path.joinpath(_MODEL_FILE_NAME)


def get_settings_file_path(clip_type):
    dir_path = get_data_dir_path(clip_type)
    return dir_path.joinpath(_SETTINGS_FILE_NAME)
