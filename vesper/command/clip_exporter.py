"""Module containing class `ClipExporter`."""


import logging

from vesper.django.app.models import Job
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils


class ClipExporter:
    
    """
    Exports clips to sound files.
    
    The sound files are written to the server-side directory specified in
    the `output_dir_path` argument. The name of each sound file is
    created from clip metadata with the aid of a clip file name formatter
    extension, specified by the `clip_file_name_formatter` argument.
    """
        
    
    extension_name = 'Clip Exporter'
    
    
    def __init__(self, args):
        
        
        self.output_dir_path = command_utils.get_required_arg(
            'output_dir_path', args)
        
        spec = command_utils.get_required_arg(
            'clip_file_name_formatter', args)
        self.file_name_formatter = _create_file_name_formatter(spec)
    
    
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)
        self._logger = logging.getLogger()
        
        try:
            self._logger.info('ClipExporter.execute')
            self._logger.info(str(self.file_name_formatter))
#             recordings = self._get_recordings()
#             self._log_recordings(recordings)
#             with transaction.atomic():
#                 self._add_recordings(recordings)
            
        except Exception as e:
            self._logger.error((
                'Recording import failed with an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

        return True
            
            
# def _get_clip_query(keyword_args):
#     station_names = get_station_names(keyword_args)
#     detector_names = get_detector_names(keyword_args)
#     clip_class_names = get_clip_class_names(keyword_args)
#     start_night, end_night = get_nights(keyword_args)
#     return (station_names, detector_names, clip_class_names, start_night,
#             end_night)


def _create_file_name_formatter(spec):
    
    formatter_classes = \
        extension_manager.instance.get_extensions('Clip File Name Formatter')
    formatter_class = formatter_classes[spec['name']]
    return formatter_class()


class SimpleClipFileNameFormatter:
    
    """Formats clip file names."""
    
    
    extension_name = 'Simple Clip File Name Formatter'
    
    
    def format_file_name(self, clip):
    
        """Creates a file name for the specified clip."""
        
        return 'clip_{}.wav'.format(clip.id)


# def _create_clip_file_name(station_name, detector_name, start_time):
#     ms = int(round(start_time.microsecond / 1000.))
#     start_time = start_time.strftime('%Y-%m-%d_%H.%M.%S') + \
#         '.{:03d}'.format(ms) + '_Z'
#     return '{:s}_{:s}_{:s}{:s}'.format(
#         station_name, detector_name, start_time, _CLIP_FILE_NAME_EXTENSION)
