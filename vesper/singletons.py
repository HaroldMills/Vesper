"""Module containing Vesper singleton objects."""


from vesper.archive_paths import archive_paths
from vesper.command.job_manager import JobManager
from vesper.django.app.archive import Archive
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preference_manager import PreferenceManager
from vesper.util.preset_manager import PresetManager
from vesper.util.recording_manager import RecordingManager
from vesper.util.singleton import Singleton


# TODO: Get rid of this module and the `Singleton` module by moving
# singletons to the modules that define their classes. This will allow
# programmers to use singletons, for example the plugin manager, by
# writing things like:
#
#     from vesper.plugin.plugin_manager import plugin_manager
#
#     detectors = plugin_manager.get_plugins('Detector')
#
# rather than:
#
#     from vesper.singletons import plugin_manager
#
#     detectors = plugin_manager.instance.get_plugins('Detector')


def _create_extension_manager():
    return ExtensionManager()


extension_manager = Singleton(_create_extension_manager)


def _create_preset_manager():
    preset_types = extension_manager.instance.get_extensions('Preset')
    preset_types = list(preset_types.values())
    preset_dir_path = str(archive_paths.preset_dir_path)
    return PresetManager(preset_types, preset_dir_path)
    
    
preset_manager = Singleton(_create_preset_manager)


def _create_preference_manager():
    return PreferenceManager(archive_paths.preference_file_path)


preference_manager = Singleton(_create_preference_manager)


job_manager = Singleton(JobManager)
     
     
def _create_clip_manager():
    from vesper.util.clip_manager import ClipManager
    return ClipManager()


clip_manager = Singleton(_create_clip_manager)
                         
                         
def _create_recording_manager():
    return RecordingManager(
        archive_paths.archive_dir_path, archive_paths.recording_dir_paths)


recording_manager = Singleton(_create_recording_manager)


def _create_archive():
    return Archive()


archive = Singleton(_create_archive)
