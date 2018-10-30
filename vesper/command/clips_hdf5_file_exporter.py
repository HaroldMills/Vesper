"""Module containing class `ClassifierTrainingClipsExporter`."""


import logging

import h5py
import math

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
from vesper.singletons import clip_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.annotation_utils as annotation_utils


# TODO: Make detector name and output sample rate command arguments.


# Settings for exports from 2017 MPG Ranch archive for 2018 coarse
# classifier training.
_DETECTOR_NAME = 'Tseep'
_CLASSIFICATION_ANNOTATION_NAME = 'Classification'
_CLASSIFICATIONS = ['Call*', 'Noise']
_OTHER_ANNOTATION_NAMES = []
_DEFAULT_ANNOTATION_VALUES = {}
_EXTRACTION_START_OFFSETS = {
    'Tseep': -.1,
    'Thrush': -.1
}
_EXTRACTION_DURATIONS = {
    'Tseep': .5,
    'Thrush': .6
}
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
        
        self._classifications_regexp = \
            annotation_utils.create_string_annotation_values_regexp(
                _CLASSIFICATIONS)
    
        self._extraction_start_offset = \
            _EXTRACTION_START_OFFSETS[_DETECTOR_NAME]
            
        self._extraction_duration = _EXTRACTION_DURATIONS[_DETECTOR_NAME]
            
        self._clip_manager = clip_manager.instance
        
    
    def export(self, clip):
        
        classification = self._get_annotation_value(
            clip, _CLASSIFICATION_ANNOTATION_NAME)
        
        if classification is not None and \
                self._classifications_regexp.match(classification) is not None:
            
            result = self._extract_samples(clip)
            
            if result is not None:
                
                samples, start_index = result
                
                # Create dataset from clip samples.
                name = '/clips/{:08d}'.format(clip.id)
                self._file[name] = samples
                
                # Set dataset attributes from clip metadata.
                attrs = self._file[name].attrs
                attrs['clip_id'] = clip.id
                attrs['station'] = clip.station.name
                attrs['mic_output'] = clip.mic_output.name
                attrs['detector'] = clip.creating_processor.name
                attrs['date'] = str(clip.date)
                attrs['sample_rate'] = clip.sample_rate
                attrs['clip_start_time'] = _format_datetime(clip.start_time)
                attrs['clip_start_index'] = clip.start_index
                attrs['clip_length'] = clip.length
                attrs['extraction_start_index'] = start_index
                
                annotations = self._get_annotations(clip)
                for name, value in annotations.items():
                    name = name.lower().replace(' ', '_')
                    attrs[name] = value
    
                return True
            
            else:
                return False
        
        else:
            return False
        
        
    def _get_annotation_value(self, clip, annotation_name):
        
        try:
            annotation = clip.string_annotations.get(
                info__name=annotation_name)
            
        except StringAnnotation.DoesNotExist:
            return _DEFAULT_ANNOTATION_VALUES.get(annotation_name)
        
        else:
            return annotation.value

            
    def _get_annotations(self, clip):
        
        names = [_CLASSIFICATION_ANNOTATION_NAME] + _OTHER_ANNOTATION_NAMES
        
        return dict(
            [(name, self._get_annotation_value(clip, name)) for name in names])
            
            
    def _extract_samples(self, clip):
        
        sample_rate = clip.sample_rate
        
        start_offset = _seconds_to_samples(
            self._extraction_start_offset, sample_rate)
        
        length = _seconds_to_samples(self._extraction_duration, sample_rate)
        
        try:
            samples = \
                self._clip_manager.get_samples(clip, start_offset, length)
        
        except Exception as e:
            _logger.warning((
                'Could not get samples for clip {}, so it will not appear '
                'in output. Error message was: {}').format(str(clip), str(e)))
            return None
        
        start_index = clip.start_index + start_offset
        
        return samples, start_index
    

    def end_exports(self):
        attrs = self._file['/clips'].attrs
        attrs['extraction_start_offset'] = self._extraction_start_offset
        attrs['extraction_duration'] = self._extraction_duration


def _seconds_to_samples(duration, sample_rate):
    sign = -1 if duration < 0 else 1
    return sign * int(math.ceil(abs(duration) * sample_rate))
    

def _format_datetime(dt):
    return dt.strftime(_START_TIME_FORMAT)
