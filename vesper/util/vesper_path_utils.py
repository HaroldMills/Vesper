"""Utility functions pertaining to file system paths."""


import os.path

from vesper.django.project.settings import VESPER_DATA_DIR


def get_path(*dir_names):
    return os.path.join(VESPER_DATA_DIR, *dir_names)
