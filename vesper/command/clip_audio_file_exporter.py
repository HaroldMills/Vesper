"""Module containing class `ClipAudioFileExporter`."""


from datetime import timedelta as TimeDelta
import logging
import os.path

from vesper.command.clip_exporter import ClipExporter
from vesper.command.command import CommandExecutionError
from vesper.singleton.archive import archive
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.extension_manager import extension_manager
from vesper.singleton.preset_manager import preset_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.clip_time_interval_utils as clip_time_interval_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils


_DEFAULT_TIME_INTERVAL = Bunch(
    left_padding=0,
    right_padding=0,
    offset=0)


_logger = logging.getLogger()


class ClipAudioFileExporter(ClipExporter):
    
    """
    Exports clip audio files.
    
    The audio files are written to the server-side directory specified in
    the `output_dir_path` argument. The name of each audio file is
    created from clip metadata with the aid of a clip file name formatter
    extension, specified by the `clip_file_name_formatter` argument.
    """
        
    
    extension_name = 'Clip Audio File Exporter'
    
    
    def __init__(self, args):
    
        get = command_utils.get_required_arg
        self._settings_preset_name = \
            get('clip_audio_file_export_settings_preset', args)
        self._output_dir_path = get('output_dir_path', args)
        spec = get('clip_file_name_formatter', args)
        
        self._time_interval = \
            _parse_settings_preset(self._settings_preset_name)

        self._file_name_formatter = _create_file_name_formatter(spec)
    
    
    def begin_exports(self):
        try:
            os_utils.create_directory(self._output_dir_path)
        except OSError as e:
            raise CommandExecutionError(str(e))
 
    
    def export(self, clip):

        start_offset, length = \
            clip_time_interval_utils.get_clip_time_interval(
                clip, self._time_interval)

        file_name = self._file_name_formatter.get_file_name(clip, start_offset)
        file_path = os.path.join(self._output_dir_path, file_name)

        try:
            clip_manager.export_audio_file(
                clip, file_path, start_offset, length)
        except Exception as e:
            _logger.warning(f'Could not export clip {clip}. {e}')
            return False

        return True
            
            
def _parse_settings_preset(preset_name):
    
    if preset_name == archive.NULL_CHOICE:
        # no preset specified

        return _DEFAULT_TIME_INTERVAL
    
    preset_type = 'Clip Audio File Export Settings'
    preset_path = (preset_type, preset_name)
    preset = preset_manager.get_preset(preset_path)
    data = preset.data

    time_interval = data.get('time_interval')

    if time_interval is not None:
        # preset specifies clip time interval

        try:
            return clip_time_interval_utils.parse_clip_time_interval_spec(
                time_interval)

        except Exception as e:
            _logger.warning(
                f'Error parsing {preset_type} preset "{preset_name}". '
                f'{e} Preset will be ignored.')

    return _DEFAULT_TIME_INTERVAL


def _create_file_name_formatter(spec):
    formatter_classes = extension_manager.get_extensions(
        'Clip File Name Formatter')
    formatter_class = formatter_classes[spec['name']]
    return formatter_class()
 

class SimpleClipFileNameFormatter:
     
    """Formats clip audio file names."""
     
     
    extension_name = 'Simple Clip File Name Formatter'
     
     
    def get_file_name(self, clip, start_offset):
     
        """Creates a audio file name for the specified clip."""
        
        station_name = clip.station.name
        mic_output_name = _get_mic_output_name(clip)
        detector_name = _get_detector_name(clip)
        start_time = _format_start_time(clip, start_offset)
        classification = _get_classification(clip)
        
        return (
            f'{station_name}_{mic_output_name}_{detector_name}_'
            f'{start_time}_{classification}.wav')


_SUFFIX = ' Output'


def _get_mic_output_name(clip):
    name = clip.mic_output.name
    if name.endswith(_SUFFIX):
        name = name[:-len(_SUFFIX)]
    return name

        
def _get_detector_name(clip):
    if clip.creating_processor is None:
        return 'Unknown'
    else:
        return clip.creating_processor.name
    
    
def _format_start_time(clip, start_offset):
    seconds = signal_utils.get_duration(start_offset, clip.sample_rate)
    offset = TimeDelta(seconds=seconds)
    time = clip.start_time + offset
    ms = time.microsecond // 1000
    return time.strftime('%Y-%m-%d_%H.%M.%S') + f'.{ms:03d}_Z'


def _get_classification(clip):
    annotations = model_utils.get_clip_annotations(clip)
    return annotations.get('Classification', 'Unclassified')
