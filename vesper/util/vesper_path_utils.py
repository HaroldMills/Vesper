"""Utility functions pertaining to file system paths."""


import os.path


# For consistency with Windows, we use the term *app data directory* to
# refer to the directory in which a user stores application preferences
# and presets.


_DEFAULT_APP_DATA_DIR_NAME = 'Vesper'

# TODO: Change the name of this environment variable to 'VESPER_APP_DATA'.
_APP_DATA_VAR_NAME = 'VESPER_HOME'


def get_path(key):
    
    if key == 'App Data':
        return _get_app_data_dir_path()
        
    elif key == 'Vesper Home':
        return _get_vesper_dir_path()
    
    elif key == 'User Home':
        return _get_user_home_dir_path()
    
    else:
        raise KeyError('Unrecognized path "{}".'.format(key))
    
    
# TODO: Observe OS conventions for default location of app data directory.
def _get_app_data_dir_path():
    try:
        return os.environ[_APP_DATA_VAR_NAME]
    except KeyError:
        return os.path.join(
            _get_user_home_dir_path(), _DEFAULT_APP_DATA_DIR_NAME)


def _get_user_home_dir_path():
    return os.path.expanduser('~')


def _get_vesper_dir_path(*dir_names):
    return os.path.join(_get_vesper_home_dir_path(), *dir_names)


def _get_vesper_home_dir_path():
    
    # Find Vesper package directory. We assume that the current module
    # is somewhere within this package.
    vesper_package_path = _find_ancestor_dir('vesper', __file__)
    
    # Return grandparent of Vesper package directory.
    dirname = os.path.dirname
    return dirname(dirname(vesper_package_path))


def _find_ancestor_dir(name, path):
    if os.path.basename(path) == name:
        return path
    else:
        parent_path = os.path.dirname(path)
        if parent_path == path:
            return None
        else:
            return _find_ancestor_dir(name, parent_path)
