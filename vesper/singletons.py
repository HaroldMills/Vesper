"""Module containing Vesper singleton objects."""


from vesper.archive_paths import archive_paths
from vesper.command.job_manager import JobManager
from vesper.django.app.archive import Archive
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preference_manager import PreferenceManager
from vesper.util.preset_manager import PresetManager
from vesper.util.recording_manager import RecordingManager
from vesper.util.singleton import Singleton
import tensorflow as tf


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
'''


_TF2_DETECTORS = '''
'''
# '''
# 
#     # BirdVoxDetect 0.5.x with adaptive thresholds
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT10
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT20
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT30
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT40
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT50
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT60
#     - vesper.birdvox.birdvoxdetect_0_5.detector.DetectorAT70
# 
# '''


if _TF_VERSION == 1:
    _TF_CLASSIFIERS = _TF1_CLASSIFIERS
    _TF_DETECTORS = _TF1_DETECTORS
else:
    _TF_CLASSIFIERS = _TF2_CLASSIFIERS
    _TF_DETECTORS = _TF2_DETECTORS


_EXTENSIONS_SPEC = f'''

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


def _create_extension_manager():
    return ExtensionManager(_EXTENSIONS_SPEC)


extension_manager = Singleton(_create_extension_manager)


# Import BirdVox detectors module to create BirdVox detector classes
# and add to extension manager. This is a temporary kludge that will
# not be needed in Vesper 0.5.0.
import vesper.birdvox.detectors


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
