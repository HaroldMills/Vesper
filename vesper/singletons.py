"""Module containing Vesper singleton objects."""


from vesper.django.app.job_manager import JobManager
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preset_manager import PresetManager
import vesper.util.vesper_path_utils as vesper_path_utils


extension_manager = ExtensionManager('''

Importer:
    - vesper.django.app.archive_data_importer.ArchiveDataImporter
    - vesper.django.app.recording_importer.RecordingImporter

Vesper Command:
    - vesper.django.app.import_command.ImportCommand
    - vesper.django.app.test_command.TestCommand
    
''')


def _create_preset_manager():
    preset_types = extension_manager.get_extensions('Preset Type')
    presets_dir_path = vesper_path_utils.get_path('Presets')
    return PresetManager(preset_types, presets_dir_path)
    
    
preset_manager = _create_preset_manager()


def _create_job_manager():
    command_classes = extension_manager.get_extensions('Vesper Command')
    return JobManager(command_classes)

job_manager = _create_job_manager()
