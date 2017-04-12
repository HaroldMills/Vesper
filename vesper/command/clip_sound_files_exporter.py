"""Module containing class `ClipSoundFilesExporter`."""


import logging
import os.path

from vesper.command.command import CommandExecutionError
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils
import vesper.util.os_utils as os_utils


_logger = logging.getLogger()


class ClipSoundFilesExporter:
    
    """
    Exports clip sound files.
    
    The sound files are written to the server-side directory specified in
    the `output_dir_path` argument. The name of each sound file is
    created from clip metadata with the aid of a clip file name formatter
    extension, specified by the `clip_file_name_formatter` argument.
    """
        
    
    extension_name = 'Clip Sound Files'
    
    
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
        with open(file_path, 'wb') as file_:
            file_.write(clip.wav_file_contents)
        
        
    def end_exports(self):
        pass
            
            
def _create_file_name_formatter(spec):
    formatter_classes = extension_manager.instance.get_extensions(
        'Clip File Name Formatter')
    formatter_class = formatter_classes[spec['name']]
    return formatter_class()
 
 
class SimpleClipFileNameFormatter:
     
    """Formats clip sound file names."""
     
     
    extension_name = 'Simple Clip File Name Formatter'
     
     
    def get_file_name(self, clip):
     
        """Creates a sound file name for the specified clip."""
        
        station_name = clip.station.name
        channel_num = clip.channel_num
        detector_name = _get_detector_name(clip)
        start_time = _format_start_time(clip)
        
        return '{}_{}_{}_{}.wav'.format(
            station_name, channel_num, detector_name, start_time)


def _get_detector_name(clip):
    if clip.creating_processor is None:
        return 'Unknown'
    else:
        return clip.creating_processor.name
    
    
def _format_start_time(clip):
    time = clip.start_time
    ms = int(round(time.microsecond / 1000.))
    return time.strftime('%Y-%m-%d_%H.%M.%S') + '.{:03d}'.format(ms) + '_Z'
