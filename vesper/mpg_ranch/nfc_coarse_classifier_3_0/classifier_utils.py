"""Utility functions pertaining to classifiers."""


from pathlib import Path

import numpy as np


_DATA_DIR_NAME = '{} Classifier'
_MODEL_FILE_NAME = 'Keras Model.h5'
_MODEL_DIR_NAME = 'TensorFlow Model'
_SETTINGS_FILE_NAME = 'Settings.yaml'


def get_data_dir_path(clip_type):
    package_path = Path(__file__).parent
    dir_name = _DATA_DIR_NAME.format(clip_type)
    return package_path.joinpath(dir_name)


def get_model_file_path(clip_type):
    dir_path = get_data_dir_path(clip_type)
    return dir_path.joinpath(_MODEL_FILE_NAME)


def get_model_dir_path(clip_type):
    data_dir_path = get_data_dir_path(clip_type)
    return data_dir_path / _MODEL_DIR_NAME


def get_settings_file_path(clip_type):
    dir_path = get_data_dir_path(clip_type)
    return dir_path.joinpath(_SETTINGS_FILE_NAME)


def score_dataset_examples(estimator, dataset_creator):
    
    """
    Runs a TensorFlow estimator on each element of a dataset,
    returning the resulting scores in a NumPy array.
    """
    
    scores = estimator.predict(input_fn=dataset_creator)
    
    # At this point `scores` is an iterator that yields
    # dictionaries, each of which contains a single item whose
    # value is an array containing one element, a score. Extract
    # the scores into a NumPy array.
    scores = np.array([list(s.values())[0][0] for s in scores])
    
    return scores
