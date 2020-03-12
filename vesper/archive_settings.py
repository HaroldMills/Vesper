"""
Vesper archive settings.

The Vesper server serves the Vesper archive that is in the directory
in which the server starts. The archive settings are the composition
of a set of default settings (hard-coded in this module) and settings
(optionally) specified in the file "Archive Settings.yaml" in the
archive directory.
"""


from pathlib import Path
import os
import sys

from vesper.util.settings import Settings
from vesper.util.settings_type import SettingsType
import vesper.archive_paths as archive_paths


_DEFAULT_SETTINGS = Settings.create_from_yaml('''
database:
    engine: SQLite
''')


_SETTINGS_TYPE = SettingsType('Archive Settings', _DEFAULT_SETTINGS)


_SETTINGS_FILE_NAME = 'Archive Settings.yaml'


def _create_settings():
    archive_dir_path = Path(os.getcwd())
    settings = _load_settings_file(archive_dir_path)
    archive_paths.initialize(archive_dir_path, settings)
    return settings

    
def _load_settings_file(archive_dir_path):
    
    file_path = archive_dir_path / _SETTINGS_FILE_NAME
    
    if not file_path.exists():
        # settings file doex not exist
        
        return _SETTINGS_TYPE.defaults
    
    else:
        # settings file exists
        
        try:
            return _SETTINGS_TYPE.create_settings_from_yaml_file(file_path)
        
        except Exception as e:
            print((
                'Load failed for settings file "{}". Error message '
                'was: {}').format(file_path, str(e)))
            sys.exit(1)
    
    
archive_settings = _create_settings()
