"""Module containing Vesper singleton objects."""


from vesper.command.job_manager import JobManager
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preference_manager import PreferenceManager
from vesper.util.preset_manager import PresetManager
from vesper.util.singleton import Singleton
import vesper.util.vesper_path_utils as vesper_path_utils


_EXTENSIONS_SPEC = '''

Classifier:
    - vesper.mpg_ranch.coarse_classifier.CoarseClassifier
    - vesper.mpg_ranch.outside_classifier.OutsideClassifier
    - vesper.mpg_ranch.species_classifier.SpeciesClassifier
    
Command:
    - vesper.command.classify_command.ClassifyCommand
    - vesper.command.detect_command.DetectCommand
    - vesper.command.export_command.ExportCommand
    - vesper.command.import_command.ImportCommand
    - vesper.command.test_command.TestCommand
    
Exporter:
    - vesper.command.clip_sound_files_exporter.ClipSoundFilesExporter
    - vesper.mpg_ranch.clips_csv_file_exporter.ClipsCsvFileExporter
    
Importer:
    - vesper.command.archive_data_importer.ArchiveDataImporter
    - vesper.command.recording_importer.RecordingImporter

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
    presets_dir_path = vesper_path_utils.get_archive_path('Presets')
    return PresetManager(preset_types, presets_dir_path)
    
preset_manager = Singleton(_create_preset_manager)


def _create_preference_manager():
    preferences_dir_path = vesper_path_utils.get_archive_path()
    return PreferenceManager(preferences_dir_path)

preference_manager = Singleton(_create_preference_manager)


job_manager = Singleton(JobManager)
