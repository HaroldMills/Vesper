from vesper.archive_paths import archive_paths
from vesper.util.recording_manager import RecordingManager


recording_manager = RecordingManager(
    archive_paths.archive_dir_path, archive_paths.recording_dir_paths)