"""Provides access to the extensions of a program."""


# As of Python 3.10.10, if we just do `import importlib`, then
# `importlib` is defined (as expected) but `importlib.metadata` is not
# (which surprises me, and I believe it was defined in an earlier
# Python 3.10.x). If we do `import importlib.metadata`, however, then
# both `importlib` and `importlib.metadata` are defined.
import importlib.metadata

import itertools

from django.db.models import Q

from vesper.django.app.models import Processor
import vesper.birdvox.detectors as birdvox_detectors
import vesper.django.project.settings as settings
import vesper.util.yaml_utils as yaml_utils


# Note that even though the `ExtensionManager` class is typically used as a
# singleton, we make it a class rather than a module to facilitate testing.
#
# Note also that rather than loading extensions eagerly in the `__init__`
# method, an `ExtensionManager` instead loads them lazily in its
# `get_extensions` method. Loading extensions in the `__init__` method
# would not work since we want to allow extension modules to use the
# extension manager on import, but it is not available until after its
# `__init__` method executes.
#
# The `get_extensions` method also loads extensions only of the requested
# type. This avoids loading extensions of types that are never used.

# TODO: Would it be possible to load extension modules and their
# dependencies only when they are actually used? This might be
# accomplished by separating extension metadata from code modules and
# only loading the code modules when they are actually needed. This
# would help avoid unnecessary and undesirable imports in some cases.

# TODO: Use a hierarchical name space for plugins, extension points, and
# extensions?


def _chain(iterable):
    return itertools.chain.from_iterable(iterable)
        

if settings.VESPER_INCLUDE_TENSORFLOW_PROCESSORS:

    import tensorflow as tf

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

    # MPG Ranch
    - vesper.mpg_ranch.nfc_bounding_interval_annotator_1_0.annotator.Annotator
    - vesper.mpg_ranch.nfc_coarse_classifier_3_1.classifier.Classifier
    - vesper.mpg_ranch.nfc_coarse_classifier_4_1.classifier.Classifier
    
    # PSW
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier10
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier20
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier30
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier40
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier50
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier60
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier70
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier80
    - vesper.psw.nogo_coarse_classifier_0_0.classifier.Classifier90
    
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
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector70_25
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector70_12
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector80
    - vesper.mpg_ranch.nfc_detector_1_1.detector.ThrushDetector90
    
    # MPG Ranch Tseep Detector 1.1
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector20
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector30
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector40
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector50
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector60
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector60_25
    - vesper.mpg_ranch.nfc_detector_1_1.detector.TseepDetector60_12
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

else:
    # don't include TensorFlow processors.

    _TF_CLASSIFIERS = ''
    _TF_DETECTORS = ''


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
    - vesper.command.create_random_clips_command.CreateRandomClipsCommand
    - vesper.command.delete_clip_audio_files_command.DeleteClipAudioFilesCommand
    - vesper.command.delete_clips_command.DeleteClipsCommand
    - vesper.command.delete_recordings_command.DeleteRecordingsCommand
    - vesper.command.detect_command.DetectCommand
    - vesper.command.execute_deferred_actions_command.ExecuteDeferredActionsCommand
    - vesper.command.export_clip_counts_by_classification_to_csv_file_command.ExportClipCountsByClassificationToCsvFileCommand
    - vesper.command.export_clip_counts_by_tag_to_csv_file_command.ExportClipCountsByTagToCsvFileCommand
    - vesper.command.export_command.ExportCommand
    - vesper.command.import_command.ImportCommand
    - vesper.command.refresh_recording_audio_file_paths_command.RefreshRecordingAudioFilePathsCommand
    - vesper.command.tag_clips_command.TagClipsCommand
    - vesper.command.test_command.TestCommand
    - vesper.command.transfer_clip_classifications_command.TransferClipClassificationsCommand
    - vesper.command.untag_clips_command.UntagClipsCommand
    - vesper.old_bird.add_old_bird_clip_start_indices_command.AddOldBirdClipStartIndicesCommand
    
Detector:

{_TF_DETECTORS}

    # Old Bird redux detectors 1.0
    - vesper.old_bird.old_bird_detector_redux_1_0.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_0.TseepDetector
    
    # Old Bird redux detectors 1.1
    - vesper.old_bird.old_bird_detector_redux_1_1.ThrushDetector
    - vesper.old_bird.old_bird_detector_redux_1_1.TseepDetector
    
    # Pacific Southwest (PSW) Research Station detectors
    - vesper.psw.nogo_detector_0_0.detector.Detector
    
Exporter:
    - vesper.command.clip_audio_file_exporter.ClipAudioFileExporter
    - vesper.command.clip_hdf5_file_exporter.ClipHdf5FileExporter
    - vesper.command.clip_metadata_csv_file_exporter.ClipMetadataCsvFileExporter
    
Importer:
    - vesper.command.metadata_importer.MetadataImporter
    - vesper.command.recording_importer.RecordingImporter
    - vesper.old_bird.clip_importer.ClipImporter

Preset:
    - vesper.command.clip_audio_file_export_settings_preset.ClipAudioFileExportSettingsPreset
    - vesper.command.clip_hdf5_file_export_settings_preset.ClipHdf5FileExportSettingsPreset
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

            extensions += self._get_detector_provider_detector_classes()
            
        return extensions
    
    
    def _get_detector_provider_detector_classes(self):

        entry_points = importlib.metadata.entry_points(
            group='vesper.detector_providers')
        
        return list(_chain(
            self._get_detector_provider_detector_classes_aux(entry_point)
            for entry_point in entry_points))
    

    def _get_detector_provider_detector_classes_aux(self, entry_point):

        try:

            provider = entry_point.load()

            series_names = provider.get_supported_detector_series_names()

            return _chain(
                self._get_detector_series_classes(series_name, provider)
                for series_name in series_names)
        
        except Exception:
            return []
    

    def _get_detector_series_classes(self, series_name, provider):

        detectors = Processor.objects.filter(
            Q(type='Detector') & Q(name__startswith=series_name))
        
        return [
            self._get_detector_class(detector, provider)
            for detector in detectors]
    

    def _get_detector_class(self, detector, provider):
         
        extension_name = detector.name

        parts = extension_name.split()
        series_name = parts[0]
        version_number = parts[1]
        settings = parts[2:]

        settings = provider.parse_detector_settings(
            series_name, version_number, settings)
        
        return provider.get_detector_class(
            extension_name, series_name, version_number, settings)
    
        
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
