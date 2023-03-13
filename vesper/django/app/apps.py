from pathlib import Path
import logging

from django.apps import AppConfig
from django.conf import settings

from vesper.archive_paths import archive_paths
import vesper.util.archive_lock as archive_lock
import vesper.util.yaml_utils as yaml_utils


class VesperConfig(AppConfig):
    

    name = 'vesper.django.app'
    label = 'vesper'
    

    def ready(self):
        
        # Put code here to run once on startup.
        
        # print('vesper.django.app.apps.VesperConfig.ready')

        _set_archive_paths()
        
        # Create the one and only archive lock.
        archive_lock.create_lock()


def _set_archive_paths():
    
    archive_dir_path = settings.VESPER_ARCHIVE_DIR_PATH

    p = archive_paths

    p.archive_dir_path = archive_dir_path
    p.clip_dir_path = archive_dir_path / 'Clips'
    p.deferred_action_dir_path = archive_dir_path / 'Deferred Actions'
    p.job_log_dir_path = archive_dir_path / 'Logs' / 'Jobs'
    p.preference_file_path = archive_dir_path / 'Preferences.yaml'
    p.preset_dir_path = archive_dir_path / 'Presets'
    p.recording_dir_paths = _get_recording_dir_paths(archive_dir_path)


def _get_recording_dir_paths(archive_dir_path):

    """
    Gets the list of recording directory paths of this Vesper archive.

    The list is obtained according to the following rules:

    1. If the file "Archive Settings.yaml" exists in the archive
       directory and contains a `recording_directories` item, the
       item's value is the list.

    2. Otherwise, if there are one or more "/Recordings*" directories,
       the list contains those directories.

    3. Otherwise, if there are one or more "<archive_dir_path>/Recordings*"
       directories, the list contains those directories.

    4. Otherwise, the list is the empty list. This is the norm for
       an archive that has clip audio files but not recording audio
       files.
    """

    # Try to get paths from archive settings file.
    paths = _get_archive_settings_recording_dir_paths(archive_dir_path)
    if paths is not None:
        return paths

    # Try to get paths of the form /Recordings*.
    paths = _get_recording_subdir_paths(Path('/'))
    if len(paths) != 0:
        return paths
    
    # Try to get paths of the form <archive_dir_path>/Recordings*.
    return _get_recording_subdir_paths(archive_dir_path)


def _get_archive_settings_recording_dir_paths(archive_dir_path):

    path = archive_dir_path / 'Archive Settings.yaml'
    
    if path.is_file():
        # archive settings file present in archive directory

        try:
            settings = yaml_utils.load(path)

        except Exception as e:
            logging.warning(
                f'Attempt to load archive settings file "{path}" raised '
                f'exception. File will be ignored. Exception message was: '
                f'{e}')
            return None
        
        if settings is None:
            # settings file contains no settings

            return None
        
        if isinstance(settings, dict):
            # settings file contains associative array

            try:
                paths = settings['recording_directories']
            except KeyError:
                return None
            
            return [Path(p) for p in paths]
        
        else:
            # settings file is not empty but does not contain an
            # associative array

            logging.warning(
                f'Archive settings file "{path}" does not contain an '
                f'associative array as expected. File will be ignored.')
            return None
    

def _get_recording_subdir_paths(parent_dir_path):

    # Get paths of subdirectories whose names start with "Recordings".
    paths = [
        p for p in parent_dir_path.iterdir()
        if p.is_dir() and p.name.startswith('Recordings')]
    
    # Sort paths by subdirectory name.
    paths.sort(key=lambda p: p.name)
    
    return paths

