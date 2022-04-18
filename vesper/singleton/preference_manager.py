from vesper.archive_paths import archive_paths
from vesper.util.preference_manager import PreferenceManager


preference_manager = \
    PreferenceManager.create_for_file(archive_paths.preference_file_path)
