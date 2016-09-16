"""Utility functions pertaining to file system paths."""


import os.path

from vesper.django.project.settings import VESPER_ARCHIVE_DIR_PATH


def get_archive_dir_path(*dir_names):
    return os.path.join(VESPER_ARCHIVE_DIR_PATH, *dir_names)
