"""Utility functions pertaining to file system paths."""


import os.path

from vesper.django.project.settings import VESPER_ARCHIVE_DIR_PATH


def get_archive_path(*parts):
    return os.path.join(VESPER_ARCHIVE_DIR_PATH, *parts)
