"""Module for accessing Vesper viewer preferences."""


import os
import sys

import vesper.util.os_utils as os_utils
import vesper.util.vesper_path_utils as vesper_path_utils
        
            
_DEFAULT_PREFERENCES_FILE_NAME = 'Preferences.yaml'


_preferences = {}


def load_preferences(file_name=_DEFAULT_PREFERENCES_FILE_NAME):
    
    # Get preferences file path.
    dir_path = vesper_path_utils.get_path('App Data')
    file_path = os.path.join(dir_path, file_name)
        
    global _preferences
    
    try:
        _preferences = os_utils.read_yaml_file(file_path)
        
    except OSError as e:
        # TODO: Handle `OSError` exceptions at call sites rather than here.
        # TODO: Maybe we should use default preferences if read fails?
        print(str(e), file=sys.stderr)
        sys.exit(1)


# TODO: Require default argument? Or perhaps we should require that each
# preference be registered before use, including a name, type, and default
# value.
def get(name, default=None):
    return _preferences.get(name, default)
