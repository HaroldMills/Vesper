"""Module containing class `ClipsHdf5FileExporter`."""


import logging

import h5py
import math

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
from vesper.singleton.clip_manager import clip_manager
import vesper.command.command_utils as command_utils


# TODO: Make reading clip ids and classifications from output files faster?


# Settings for exports from 2017 and 2018 MPG Ranch archives for coarse
# classifier training.
# _EXTRACTION_START_OFFSETS = {
#     'Tseep': -.1,
#     'Thrush': -.05
# }
# _EXTRACTION_DURATIONS = {
#     'Tseep': .5,
#     'Thrush': .65
# }
# _ANNOTATION_NAMES = ['Classification']
# _DEFAULT_ANNOTATION_VALUES = {}
# _START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


# Settings for exports from 2018 MPG Ranch archives for species classifier
# training.
_EXTRACTION_START_OFFSETS = {
    'Tseep': -.5,
    'Thrush': -.5
}
_EXTRACTION_DURATIONS = {
    'Tseep': 1.2,
    'Thrush': 1.2
}
_ANNOTATION_INFOS = [
    ('Classification', None), 
    ('Call Start Index', int), 
    ('Call End Index', int)]
_DEFAULT_ANNOTATION_VALUES = {}
_START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


# # Settings for exports from 2017 MPG Ranch Archive 30k for NFC time bound
# # marker training.
# _EXTRACTION_START_OFFSETS = {
#     'Tseep': -.5,
#     'Thrush': -.5
# }
# _EXTRACTION_DURATIONS = {
#     'Tseep': 1.2,
#     'Thrush': 1.5
# }
# _ANNOTATION_INFOS = [
#     ('Classification', None), 
#     ('Call Start Index', int), 
#     ('Call End Index', int)]
# _DEFAULT_ANNOTATION_VALUES = {}
# _START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


_logger = logging.getLogger()


class ClipsHdf5FileExporter:
    
    """
    Exports clips to an HDF5 file.
    
    The clips are written to the server-side HDF5 file specified in
    the `output_file_path` argument.
    """
        
    
    extension_name = 'Clips HDF5 File Exporter'
    
    
    def __init__(self, args):
        self._output_file_path = \
            command_utils.get_required_arg('output_file_path', args)
    
    
    def begin_exports(self):
        
        try:
            self._file = h5py.File(self._output_file_path, 'w')
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        # Always create the "clips" group, even if it will be empty.
        self._file.create_group('/clips')
        
    
    def export(self, clip):
        
        annotations = _get_annotations(clip)
        
        result = self._extract_samples(clip, annotations)
        
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
            
            for name, value in annotations.items():
                name = name.lower().replace(' ', '_')
                try:
                    attrs[name] = value
                except Exception:
                    _logger.error(
                        f'Could not assign value "{value}" for attribute '
                        f'"{name}" for clip starting at {clip.start_time}.')
                    raise
                
            return True
        
        else:
            return False
        
 
    def _extract_samples(self, clip, annotations):
        
        extent = _get_extraction_extent(clip, annotations)
        
        if extent is None:
            return None
        
        else:
            
            start_offset, length = extent
            
            try:
                samples = clip_manager.get_samples(clip, start_offset, length)
            
            except Exception as e:
                _logger.warning(
                    f'Could not get samples for clip {clip}, so it will '
                    f'not appear in output. Error message was: {e}')
                return None
            
            start_index = clip.start_index + start_offset
            
            return samples, start_index
    

    def end_exports(self):
        pass


def _get_extraction_extent(clip, annotations):
    
    detector_name = _get_detector_name(clip)
    
    if detector_name is None:
        return None
    
    else:
        
        # Get start offset and duration in seconds.
        start_offset = _EXTRACTION_START_OFFSETS[detector_name]
        duration = _EXTRACTION_DURATIONS[detector_name]
        
        # Convert to samples.
        sample_rate = clip.sample_rate
        start_offset = _seconds_to_samples(start_offset, sample_rate)
        length = _seconds_to_samples(duration, sample_rate)
        
        # Get call start index.
        call_start_index = annotations['Call Start Index']
        if call_start_index is None:
            raise ValueError(f'Call start index missing for clip {clip}.')
        
        # Make start offset relative to clip start index rather
        # than call start index.
        start_offset += call_start_index - clip.start_index
        
        return start_offset, length
        

# def _get_extraction_extent(clip, annotations):
#     
#     detector_name = _get_detector_name(clip)
#     
#     if detector_name is None:
#         return None
#     
#     else:
#         
#         # Get start offset and duration in seconds.
#         start_offset = _EXTRACTION_START_OFFSETS[detector_name]
#         duration = _EXTRACTION_DURATIONS[detector_name]
#         
#         # Convert to samples.
#         sample_rate = clip.sample_rate
#         start_offset = _seconds_to_samples(start_offset, sample_rate)
#         length = _seconds_to_samples(duration, sample_rate)
#         
#         return start_offset, length
        

def _get_detector_name(clip):
    
    detector_name = clip.creating_processor.name
    
    if detector_name.find('Thrush') != -1:
        return 'Thrush'
    
    elif detector_name.find('Tseep') != -1:
        return 'Tseep'
    
    else:
        return None
    
    
def _seconds_to_samples(duration, sample_rate):
    sign = -1 if duration < 0 else 1
    return sign * int(math.ceil(abs(duration) * sample_rate))

            
def _format_datetime(dt):
    return dt.strftime(_START_TIME_FORMAT)
    

def _get_annotations(clip):
    
    return dict([
        (name, _get_annotation_value(clip, name, value_converter))
        for name, value_converter in _ANNOTATION_INFOS])
        
        
def _get_annotation_value(clip, annotation_name, value_converter):
    
    try:
        annotation = clip.string_annotations.get(
            info__name=annotation_name)
        
    except StringAnnotation.DoesNotExist:
        return _DEFAULT_ANNOTATION_VALUES.get(annotation_name)
    
    else:
        
        if value_converter is None:
            return annotation.value
        else:
            return value_converter(annotation.value)
