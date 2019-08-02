"""Module containing Vesper singleton objects."""


from vesper.archive_paths import archive_paths
from vesper.command.job_manager import JobManager
from vesper.django.app.archive import Archive
from vesper.util.extension_manager import ExtensionManager
from vesper.util.preference_manager import PreferenceManager
from vesper.util.preset_manager import PresetManager
from vesper.util.recording_manager import RecordingManager
from vesper.util.singleton import Singleton


_EXTENSIONS_SPEC = '''

Classifier:
    - vesper.mpg_ranch.nfc_coarse_classifier_2_1.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_3_0.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_4_0.classifier.Classifier
    - vesper.mpg_ranch.nfc_detector_low_score_classifier_1_0.classifier.Classifier
    - vesper.mpg_ranch.outside_classifier.OutsideClassifier
    
Command:
    - vesper.command.adjust_clips_command.AdjustClipsCommand
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
    - vesper.command.update_recording_file_paths_command.UpdateRecordingFilePathsCommand
    
Detector:
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT02
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT05
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT05a
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT10
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT20
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT30
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT40
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT50
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT60
    - vesper.birdvox.birdvoxdetect_0_1_a0.detector.DetectorAT70
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector90
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_0_0.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector90
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_0_0.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector90
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_0_1.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector90
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_0_1.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector90
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector80
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector70
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector30
    - vesper.mpg_ranch.nfc_detector_1_0.detector.TseepDetector20
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector90
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector70
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector60
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector50
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector40
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector30
    - vesper.mpg_ranch.nfc_detector_1_0.detector.ThrushDetector20
    - vesper.old_bird.old_bird_detector_redux_1_0.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_0.TseepDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.TseepDetector
    
Exporter:
    - vesper.command.clip_audio_files_exporter.ClipAudioFilesExporter
    - vesper.mpg_ranch.clips_csv_file_exporter.ClipsCsvFileExporter
    - vesper.command.clips_hdf5_file_exporter.ClipsHdf5FileExporter
    
Importer:
    - vesper.command.archive_data_importer.ArchiveDataImporter
    - vesper.command.recording_importer.RecordingImporter
    - vesper.old_bird.clip_importer.ClipImporter

Preset:
    - vesper.command.detection_schedule_preset.DetectionSchedulePreset
    - vesper.command.station_name_aliases_preset.StationNameAliasesPreset
    - vesper.django.app.clip_album_commands_preset.ClipAlbumCommandsPreset
    - vesper.django.app.clip_album_settings_preset.ClipAlbumSettingsPreset
    
Recording File Parser:
    - vesper.mpg_ranch.recording_file_parser.RecordingFileParser
    
Clip File Name Formatter:
    - vesper.command.clip_audio_files_exporter.SimpleClipFileNameFormatter
    
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
