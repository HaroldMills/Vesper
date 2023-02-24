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

    1. If the file 'Archive Settings.yaml' exists in the archive
       directory and contains a `recording_directories` item, the
       item's value is the list.

    2. Otherwise, if there is a '/Recordings' directory, the list
       contains just that directory.

    3. Otherwise, if there is a 'Recordings' subdirectory of the
       archive directory, the list contains just that directory.

    4. Otherwise, the list is the empty list. This is the norm for
       an archive that has clip audio files but not recording audio
       files.
    """

    # TODO: Support /Recordings* and /Archive/Recordings* recording dirs.


    # Try to get paths from archive settings file.
    paths = _get_archive_settings_recording_dir_paths(archive_dir_path)

    if paths is None:
        # couldn't get paths from archive settings file.

        # Get the three possible standard recording directory paths.
        path_a = Path('/Recordings')
        path_b = archive_dir_path / 'Recordings'

        if path_a.is_dir():
            # `path_a` exists and is a directory

            paths = [path_a]

        elif path_b.is_dir():
            # `path_b` exists and is a directory

            paths = [path_b]

        else:
            # neither `path_a` nor `path_b` exists and is a directory

            paths = []

    return paths


def _get_archive_settings_recording_dir_paths(archive_dir_path):

    path = archive_dir_path / 'Archive Settings.yaml'
    
    if path.is_file():
        # archive settings file present in archive directory

        try:
            settings = yaml_utils.load(path)

        except Exception as e:
            logging.warning(
                f'Attempt to load YAML file "{path}" raised exception. '
                f'File will be ignored. Exception message was: {e}')
            return None

        try:
            paths = settings['recording_directories']
        except KeyError:
            return None
        
        return [Path(p) for p in paths]
