"""Utility functions pertaining to file system paths."""


import os.path


_APP_HOME_DIR_NAME = 'Vesper'
_APP_HOME_VAR_NAME = 'VESPER_HOME'


def get_app_home_dir_path():
    user_home_path = os.path.expanduser('~')
    default_app_home_path = os.path.join(user_home_path, _APP_HOME_DIR_NAME)
    return os.environ.get(_APP_HOME_VAR_NAME, default_app_home_path)
