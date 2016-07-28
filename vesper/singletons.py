"""Module containing Vesper singleton objects."""


from vesper.django.app.job_manager import JobManager
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preset_manager import PresetManager
from vesper.util.singleton import Singleton
import vesper.util.vesper_path_utils as vesper_path_utils


_EXTENSIONS_SPEC = '''

Command:
    - vesper.django.app.import_command.ImportCommand
    - vesper.django.app.test_command.TestCommand
    
Importer:
    - vesper.django.app.archive_data_importer.ArchiveDataImporter
    - vesper.django.app.recording_importer.RecordingImporter

Preset:
    - vesper.django.app.station_name_aliases_preset.StationNameAliasesPreset
    
Recording File Parser:
    - vesper.mpg_ranch.recording_file_parser.RecordingFileParser
    
'''

def _create_extension_manager():
    return ExtensionManager(_EXTENSIONS_SPEC)

extension_manager = Singleton(_create_extension_manager)


def _create_preset_manager():
    preset_types = extension_manager.instance.get_extensions('Preset')
    preset_types = list(preset_types.values())
    presets_dir_path = vesper_path_utils.get_path('Presets')
    return PresetManager(preset_types, presets_dir_path)
    
preset_manager = Singleton(_create_preset_manager)


def _create_job_manager():
    command_classes = extension_manager.instance.get_extensions('Command')
    return JobManager(command_classes)

job_manager = Singleton(_create_job_manager)