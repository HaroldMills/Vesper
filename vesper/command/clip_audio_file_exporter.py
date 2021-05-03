"""Module containing class `ClipAudioFilesExporter`."""


import logging
import os.path

from vesper.command.command import CommandExecutionError
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.extension_manager import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.os_utils as os_utils


_logger = logging.getLogger()


class ClipAudioFilesExporter:
    
    """
    Exports clip audio files.
    
    The audio files are written to the server-side directory specified in
    the `output_dir_path` argument. The name of each audio file is
    created from clip metadata with the aid of a clip file name formatter
    extension, specified by the `clip_file_name_formatter` argument.
    """
        
    
    extension_name = 'Clip Audio Files Exporter'
    
    
    def __init__(self, args):
    
        get = command_utils.get_required_arg
        self._output_dir_path = get('output_dir_path', args)
        spec = get('clip_file_name_formatter', args)
         
        self._file_name_formatter = _create_file_name_formatter(spec)
    
    
    def begin_exports(self):
        
        try:
            os_utils.create_directory(self._output_dir_path)
        except OSError as e:
            raise CommandExecutionError(str(e))
 
    
    def export(self, clip):
        file_name = self._file_name_formatter.get_file_name(clip)
        file_path = os.path.join(self._output_dir_path, file_name)
        clip_manager.export_audio_file(clip, file_path)
        return True
        
        
    def end_exports(self):
        pass
            
            
def _create_file_name_formatter(spec):
    formatter_classes = extension_manager.get_extensions(
        'Clip File Name Formatter')
    formatter_class = formatter_classes[spec['name']]
    return formatter_class()
 
 
class SimpleClipFileNameFormatter:
     
    """Formats clip audio file names."""
     
     
    extension_name = 'Simple Clip File Name Formatter'
     
     
    def get_file_name(self, clip):
     
        """Creates a audio file name for the specified clip."""
        
        station_name = clip.station.name
        mic_output_name = _get_mic_output_name(clip)
        detector_name = _get_detector_name(clip)
        start_time = _format_start_time(clip)
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
    
    
def _format_start_time(clip):
    time = clip.start_time
    ms = int(round(time.microsecond / 1000.))
    return time.strftime('%Y-%m-%d_%H.%M.%S') + f'.{ms:03d}_Z'


def _get_classification(clip):
    annotations = model_utils.get_clip_annotations(clip)
    return annotations.get('Classification', 'Unclassified')
