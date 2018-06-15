"""Module containing Vesper singleton objects."""


from vesper.archive_paths import archive_paths
from vesper.command.job_manager import JobManager
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preference_manager import PreferenceManager
from vesper.util.preset_manager import PresetManager
from vesper.util.recording_manager import RecordingManager
from vesper.util.singleton import Singleton


_EXTENSIONS_SPEC = '''

Classifier:
    - vesper.mpg_ranch.coarse_classifier.CoarseClassifier
    - vesper.mpg_ranch.nfc_coarse_classifier_2_0.classifier.Classifier
    - vesper.mpg_ranch.outside_classifier.OutsideClassifier
    - vesper.mpg_ranch.species_classifier.SpeciesClassifier
    
Command:
    - vesper.command.adjust_clips_command.AdjustClipsCommand
    - vesper.command.classify_command.ClassifyCommand
    - vesper.command.delete_clips_command.DeleteClipsCommand
    - vesper.command.delete_recordings_command.DeleteRecordingsCommand
    - vesper.command.detect_command.DetectCommand
    - vesper.command.export_command.ExportCommand
    - vesper.command.import_command.ImportCommand
    - vesper.command.test_command.TestCommand
    - vesper.command.update_recording_file_paths_command.UpdateRecordingFilePathsCommand
    
Detector:
    - vesper.old_bird.old_bird_detector_redux_1_0.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_0.TseepDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.TseepDetector
    - vesper.pnf.pnf_2017_basic_detector_1_0.ThrushDetector
    - vesper.pnf.pnf_2017_basic_detector_1_0.TseepDetector    
    
Exporter:
    - vesper.command.clip_sound_files_exporter.ClipSoundFilesExporter
    - vesper.mpg_ranch.clips_csv_file_exporter.ClipsCsvFileExporter
    - vesper.command.clips_hdf5_file_exporter.ClipsHdf5FileExporter
    
Importer:
    - vesper.command.archive_data_importer.ArchiveDataImporter
    - vesper.command.recording_importer.RecordingImporter
    - vesper.old_bird.clip_importer.ClipImporter

Preset:
    - vesper.command.station_name_aliases_preset.StationNameAliasesPreset
    - vesper.django.app.clip_album_commands_preset.ClipAlbumCommandsPreset
    - vesper.django.app.clip_album_settings_preset.ClipAlbumSettingsPreset
    
Recording File Parser:
    - vesper.mpg_ranch.recording_file_parser.RecordingFileParser
    
Clip File Name Formatter:
    - vesper.command.clip_sound_files_exporter.SimpleClipFileNameFormatter
    
'''


def _create_extension_manager():
    return ExtensionManager(_EXTENSIONS_SPEC)


extension_manager = Singleton(_create_extension_manager)


def _create_preset_manager():
    preset_types = extension_manager.instance.get_extensions('Preset')
    preset_types = list(preset_types.values())
    presets_dir_path = str(archive_paths.presets_dir_path)
    return PresetManager(preset_types, presets_dir_path)
    
    
preset_manager = Singleton(_create_preset_manager)


def _create_preference_manager():
    preferences_dir_path = str(archive_paths.archive_dir_path)
    return PreferenceManager(preferences_dir_path)


preference_manager = Singleton(_create_preference_manager)


job_manager = Singleton(JobManager)
     
     
def _create_recording_manager():
    return RecordingManager(
        archive_paths.archive_dir_path, archive_paths.recording_dir_paths)


recording_manager = Singleton(_create_recording_manager)
