from django.apps import AppConfig
from django.conf import settings

from vesper.archive_paths import archive_paths
import vesper.util.archive_lock as archive_lock


class VesperConfig(AppConfig):
    

    name = 'vesper.django.app'
    label = 'vesper'
    

    def ready(self):
        
        # Put code here to run once on startup.
        
        # print('vesper.django.app.apps.VesperConfig.ready')

        self._set_archive_paths()
        
        # Create the one and only archive lock.
        archive_lock.create_lock()


    def _set_archive_paths(self):
        
        archive_dir_path = settings.VESPER_ARCHIVE_DIR_PATH

        p = archive_paths

        p.archive_dir_path = archive_dir_path
        p.clip_dir_path = archive_dir_path / 'Clips'
        p.deferred_action_dir_path = archive_dir_path / 'Deferred Actions'
        p.job_log_dir_path = archive_dir_path / 'Logs' / 'Jobs'
        p.preference_file_path = archive_dir_path / 'Preferences.yaml'
        p.preset_dir_path = archive_dir_path / 'Presets'
        p.recording_dir_paths = self._get_recording_dir_paths(archive_dir_path)


    def _get_recording_dir_paths(self, archive_dir_path):
        if len(settings.VESPER_RECORDING_DIR_PATHS) == 0:
            return [archive_dir_path / 'Recordings']
        else:
            return settings.VESPER_RECORDING_DIR_PATHS
 

