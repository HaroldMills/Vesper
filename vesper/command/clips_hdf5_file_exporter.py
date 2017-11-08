"""Module containing class `ClassifierTrainingClipsExporter`."""


import logging

import h5py

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
import vesper.command.command_utils as command_utils
import vesper.django.app.annotation_utils as annotation_utils


_ANNOTATION_NAME = 'Classification'
_ANNOTATION_VALUE_SPECS = ['Call*', 'Noise']
_MIN_CLIP_LENGTH = 5205
_START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


_logger = logging.getLogger()


class ClipsHdf5FileExporter:
    
    """
    Exports clips to an HDF5 file.
    
    The clips are written to the server-side HDF5 file specified in
    the `output_file_path` argument.
    """
        
    
    extension_name = 'Clips HDF5 File'
    
    
    def __init__(self, args):
        self._output_file_path = \
            command_utils.get_required_arg('output_file_path', args)
    
    
    def begin_exports(self):
        
        try:
            self._file = h5py.File(self._output_file_path, 'w')
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        self._annotation_values_regexp = \
            annotation_utils.create_string_annotation_values_regexp(
                _ANNOTATION_VALUE_SPECS)
    
    
    def export(self, clip):
        
        try:
            annotation = \
                clip.string_annotations.get(info__name=_ANNOTATION_NAME)
        except StringAnnotation.DoesNotExist:
            return False
        
        value = annotation.value
        
        if self._annotation_values_regexp.match(value) is not None:
            
            samples = clip.sound.samples
            
            if len(samples) >= _MIN_CLIP_LENGTH:
                
                name = '/clips/{:08d}'.format(clip.id)
                start_time = _format_datetime(clip.start_time)
                
                self._file[name] = samples[:_MIN_CLIP_LENGTH]
                attrs = self._file[name].attrs
                attrs['id'] = clip.id
                attrs['station'] = clip.station.name
                attrs['microphone'] = clip.mic_output.device.model.name
                attrs['detector'] = clip.creating_processor.name
                attrs['night'] = str(clip.date)
                attrs['start_time'] = start_time
                attrs['sample_rate'] = clip.sample_rate
                attrs['classification'] = value
    
                return True
            
            else:
                return False
        
        else:
            return False
        
        
    def end_exports(self):
        pass
    

def _format_datetime(dt):
    return dt.strftime(_START_TIME_FORMAT)
