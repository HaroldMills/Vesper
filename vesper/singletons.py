"""Module containing Vesper singleton objects."""


from vesper.command.job_manager import JobManager
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preset_manager import PresetManager
from vesper.util.singleton import Singleton
import vesper.util.vesper_path_utils as vesper_path_utils


_EXTENSIONS_SPEC = '''

Command:
    - vesper.command.detect_command.DetectCommand
    - vesper.command.import_command.ImportCommand
    - vesper.command.test_command.TestCommand
    
Importer:
    - vesper.command.archive_data_importer.ArchiveDataImporter
    - vesper.command.recording_importer.RecordingImporter

Preset:
    - vesper.command.station_name_aliases_preset.StationNameAliasesPreset
    - vesper.django.app.annotation_commands_preset.AnnotationCommandsPreset
    - vesper.django.app.annotation_scheme_preset.AnnotationSchemePreset
    - vesper.django.app.clip_grid_settings_preset.ClipGridSettingsPreset
    
Recording File Parser:
    - vesper.mpg_ranch.recording_file_parser.RecordingFileParser
    
'''

def _create_extension_manager():
    return ExtensionManager(_EXTENSIONS_SPEC)

extension_manager = Singleton(_create_extension_manager)


def _create_preset_manager():
    preset_types = extension_manager.instance.get_extensions('Preset')
    preset_types = list(preset_types.values())
    presets_dir_path = vesper_path_utils.get_archive_dir_path('Presets')
    return PresetManager(preset_types, presets_dir_path)
    
preset_manager = Singleton(_create_preset_manager)


job_manager = Singleton(JobManager)
