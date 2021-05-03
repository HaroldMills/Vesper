"""Provides access to the extensions of a program."""


import importlib

import tensorflow as tf

import vesper.birdvox.detectors as birdvox_detectors
import vesper.util.yaml_utils as yaml_utils


# Note that even though the `ExtensionManager` class is typically used as a
# singleton, we make it a class rather than a module to facilitate testing.
#
# Note also that rather than loading extensions in the `__init__` method,
# we defer the loading until the first call to the `get_extensions` method.
# Otherwise importing the `extension_manager` module would cause an import
# cycle, since the `extension_manager` would attempt to import extension
# modules before its import had completed, some of which would in turn
# attempt to import the `extension_manager` module. Deferring the extension
# module imports allows the import of the `extension_manager` module to
# complete before they begin.


# TODO: Discover extension points and extensions in plugins rather than
# specifying them in a YAML extensions specification. Note, however, that
# it might still be desirable to be able to specify different subsets of
# installed extensions to work with at different times, say for different
# analysis projects.

# TODO: Actually, it might be best to stick with an explicit extensions
# configuration. The extension manager can be initialized much more quickly
# if you know up front what and where all of the extensions are, and this
# has become newly important since we are running Vesper commands in their
# own processes. A new extension manager is created in each of these
# processes, and it is desirable that that creation be fast.

# TODO: In order to make starting the execution of Vesper commands faster,
# it would be helpful to be able to get a single extension by its
# extension point name and extension name, importing *exactly the modules
# needed by that extension* and no others. This need could be addressed
# by a new extension manager method `get_extension` that gets a single
# extension.

# TODO: Use a hierarchical name space for plugins, extension points, and
# extensions?


_TF_VERSION = int(tf.__version__.split('.')[0])


_TF1_CLASSIFIERS = '''
    - vesper.mpg_ranch.nfc_coarse_classifier_2_1.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_4_0.classifier.Classifier
'''


_TF1_DETECTORS = '''

    # MPG Ranch Thrush Detector 0.0
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector90
     
    # MPG Ranch Tseep Detector 0.0
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector90
     
    # MPG Ranch Thrush Detector 0.1
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector90
     
    # MPG Ranch Tseep Detector 0.1
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector90
     
    # MPG Ranch Thrush Detector 1.0
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector20
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector30
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector90
     
    # MPG Ranch Tseep Detector 1.0
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector20
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector30
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector90

'''


_TF2_CLASSIFIERS = '''
    - vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator.Annotator
    - vesper.mpg_ranch.nfc_coarse_classifier_3_1.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_4_1.classifier.Classifier
'''


_TF2_DETECTORS = '''

    # MPG Ranch Thrush Detector 1.1
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector20
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector30
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector90
     
    # MPG Ranch Tseep Detector 1.1
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector20
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector30
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector90

'''


if _TF_VERSION == 1:
    _TF_CLASSIFIERS = _TF1_CLASSIFIERS
    _TF_DETECTORS = _TF1_DETECTORS
else:
    _TF_CLASSIFIERS = _TF2_CLASSIFIERS
    _TF_DETECTORS = _TF2_DETECTORS


_EXTENSION_SPEC = f'''

Classifier:

{_TF_CLASSIFIERS}

    - vesper.mpg_ranch.nfc_detector_low_score_classifier_1_0.classifier.Classifier
    - vesper.mpg_ranch.outside_classifier.OutsideClassifier
    - vesper.old_bird.lighthouse_outside_classifier.LighthouseOutsideClassifier
    
Command:
    - vesper.command.add_recording_audio_files_command.AddRecordingAudioFilesCommand
    - vesper.command.classify_command.ClassifyCommand
    - vesper.command.create_clip_audio_files_command.CreateClipAudioFilesCommand
    - vesper.command.delete_clip_audio_files_command.DeleteClipAudioFilesCommand
    - vesper.command.delete_clips_command.DeleteClipsCommand
    - vesper.command.delete_recordings_command.DeleteRecordingsCommand
    - vesper.command.detect_command.DetectCommand
    - vesper.command.execute_deferred_actions_command.ExecuteDeferredActionsCommand
    - vesper.command.export_command.ExportCommand
    - vesper.command.import_command.ImportCommand
    - vesper.command.test_command.TestCommand
    - vesper.command.transfer_call_classifications_command.TransferCallClassificationsCommand
    - vesper.command.refresh_recording_audio_file_paths_command.RefreshRecordingAudioFilePathsCommand
    - vesper.old_bird.add_old_bird_clip_start_indices_command.AddOldBirdClipStartIndicesCommand
    
Detector:

{_TF_DETECTORS}

    # Old Bird redux detectors 1.0
    - vesper.old_bird.old_bird_detector_redux_1_0.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_0.TseepDetector
    
    # Old Bird redux detectors 1.1
    - vesper.old_bird.old_bird_detector_redux_1_1.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.TseepDetector
    
Exporter:
    - vesper.command.clip_audio_file_exporter.ClipAudioFilesExporter
    - vesper.command.clips_hdf5_file_exporter.ClipsHdf5FileExporter
    - vesper.command.clip_metadata_csv_file_exporter.ClipMetadataCsvFileExporter
    
Importer:
    - vesper.command.metadata_importer.MetadataImporter
    - vesper.command.recording_importer.RecordingImporter
    - vesper.old_bird.clip_importer.ClipImporter

Preset:
    - vesper.command.clip_table_format_preset.ClipTableFormatPreset
    - vesper.command.detection_schedule_preset.DetectionSchedulePreset
    - vesper.command.station_name_aliases_preset.StationNameAliasesPreset
    - vesper.django.app.clip_album_commands_preset.ClipAlbumCommandsPreset
    - vesper.django.app.clip_album_settings_preset.ClipAlbumSettingsPreset
    
Recording File Parser:
    - vesper.mpg_ranch.recording_file_parser.RecordingFileParser
    
Clip File Name Formatter:
    - vesper.command.clip_audio_file_exporter.SimpleClipFileNameFormatter
    
'''


class ExtensionManager:
    
    
    def __init__(self, extension_spec=_EXTENSION_SPEC):
        
        self._extension_spec = yaml_utils.load(extension_spec)
        
        # Create extension dictionary that includes an item for each
        # extension point name, but don't attempt to load any extensions.
        # Loading doesn't happen until extensions are actually requested.
        extension_point_names = sorted(self._extension_spec.keys())
        self._extensions = dict((name, None) for name in extension_point_names)
        
        
    def get_extensions(self, extension_point_name):
        
        try:
            extensions = self._extensions[extension_point_name]
        except KeyError:
            raise ValueError(
                f'Unrecognized extension point name "{extension_point_name}".')
            
        if extensions is None:
            # extensions for this extension point not yet loaded
            
            extensions = self._load_extensions(extension_point_name)
            self._extensions[extension_point_name] = extensions
            # self._show_loaded_extensions(extension_point_name)
            
        return dict((e.extension_name, e) for e in extensions)
    
    
    def _load_extensions(self, extension_point_name):
        
        module_class_names = self._extension_spec[extension_point_name]
        extensions = [_load_extension(name) for name in module_class_names]
        
        if extension_point_name == 'Detector':
            
            # Load BirdVoxDetect detector extensions. These classes
            # are created dynamically according to the detectors
            # listed in the archive database, and thus cannot be
            # specified via YAML. Note that when Vesper's new plugin
            # infrastructure is complete, the extension manager will
            # need no special knowledge to get BirdVox detectors, but
            # rather will discover them at load time just like all
            # other plugins.
            extensions += birdvox_detectors.get_detector_classes()
            
        return extensions
    
    
    def _show_loaded_extensions(self, extension_point_name):
        print(f'Loaded "{extension_point_name}" extensions:')
        extensions = self._extensions[extension_point_name]
        names = sorted(e.extension_name for e in extensions)
        for name in names:
            print(f'    {name}')
                
    
def _load_extension(module_class_name):
    module_name, class_name = module_class_name.rsplit('.', 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
