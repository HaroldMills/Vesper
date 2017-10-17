"""
Module containing archive directory and file paths.

The `archive_paths` attribute of this module is a `Bunch` whose
attributes are the absolute paths of various archive directories.

This module is initialized by the `archive_settings` module, after
that module creates the archive settings.
"""


from vesper.util.bunch import Bunch


archive_paths = None


def initialize(archive_dir_path, archive_settings):
    
    global archive_paths
    
    archive_paths = Bunch(
        archive_dir_path=archive_dir_path,
        sqlite_database_file_path=archive_dir_path / 'Archive Database.sqlite',
        presets_dir_path=archive_dir_path / 'Presets',
#         recordings_dir_path=_create_recordings_dir_path(
#             archive_dir_path, archive_settings),
        clips_dir_path=archive_dir_path / 'Clips',
        job_logs_dir_path=archive_dir_path / 'Jobs' / 'Logs')
    
    
# def _create_recordings_dir_path(archive_dir_path, archive_settings):
#     
#     recordings_dir_path = Path(archive_settings.recordings_directory_path)
#     
#     if recordings_dir_path.is_absolute():
#         return recordings_dir_path
#     
#     else:
#         return archive_dir_path / recordings_dir_path
