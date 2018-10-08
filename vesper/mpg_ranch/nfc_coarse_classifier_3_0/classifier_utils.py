"""Utility functions pertaining to classifiers."""


from pathlib import Path


_ROOT_DIR_PATH = Path('/Users/harold/Desktop/Training Results')
_DATA_DIR_NAME = '{} Classifier'
_MODEL_FILE_NAME = 'Keras Model.h5'
_SETTINGS_FILE_NAME = 'Settings.yaml'
_STATS_YAML_FILE_NAME = 'Stats.yaml'
_STATS_PICKLE_FILE_NAME = 'Stats.pkl'
_PLOTS_FILE_NAME = 'Plots.pdf'


def get_data_dir_path(clip_type):
    root_dir_path = _ROOT_DIR_PATH
    # root_dir_path = Path(__file__).parent
    dir_name = _DATA_DIR_NAME.format(clip_type)
    return root_dir_path / dir_name


def get_model_file_path(clip_type):
    return _get_file_path(clip_type, _MODEL_FILE_NAME)


def _get_file_path(clip_type, file_name):
    dir_path = get_data_dir_path(clip_type)
    return dir_path / file_name


def get_settings_file_path(clip_type):
    return _get_file_path(clip_type, _SETTINGS_FILE_NAME)


def get_stats_yaml_file_path(clip_type):
    return _get_file_path(clip_type, _STATS_YAML_FILE_NAME)


def get_stats_pickle_file_path(clip_type):
    return _get_file_path(clip_type, _STATS_PICKLE_FILE_NAME)


def get_plots_file_path(clip_type):
    return _get_file_path(clip_type, _PLOTS_FILE_NAME)
