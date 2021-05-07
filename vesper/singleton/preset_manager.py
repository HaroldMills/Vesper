"""Module containing Vesper's preset manager singleton instance."""


from vesper.archive_paths import archive_paths
from vesper.singleton.extension_manager import extension_manager
from vesper.util.preset_manager import PresetManager


def _create_preset_manager():
    preset_dir_path = str(archive_paths.preset_dir_path)
    preset_types = extension_manager.get_extensions('Preset')
    preset_types = list(preset_types.values())
    return PresetManager(preset_dir_path, preset_types)
    
    
preset_manager = _create_preset_manager()
