"""Module containing class `ClassifierTrainingClipsExporter`."""


import logging

import h5py
import numpy as np
import resampy

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
from vesper.util.settings import Settings
import vesper.command.command_utils as command_utils
import vesper.django.app.annotation_utils as annotation_utils
import vesper.util.signal_utils as signal_utils


# TODO: Make detector name and output sample rate command arguments.


_DETECTOR_NAME = 'Thrush'
_ANNOTATION_NAME = 'Classification'
_ANNOTATION_VALUE_SPECS = ['Call*', 'Noise']
_OUTPUT_CLIP_SETTINGS = {
    'Tseep': Settings(duration=.236),  # 3000 / 22050 + .1
    'Thrush': Settings(duration=.326)  # 5000 / 22050 + .1
}
_OUTPUT_CLIP_SAMPLE_RATE = 22050
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
    
        self._output_clip_duration = \
            _OUTPUT_CLIP_SETTINGS[_DETECTOR_NAME].duration
            
        self._output_clip_length = signal_utils.seconds_to_frames(
            self._output_clip_duration, _OUTPUT_CLIP_SAMPLE_RATE)

        self._min_clip_lengths = {
            _OUTPUT_CLIP_SAMPLE_RATE: self._output_clip_length
        }
        
    
    def export(self, clip):
        
        try:
            annotation = \
                clip.string_annotations.get(info__name=_ANNOTATION_NAME)
        except StringAnnotation.DoesNotExist:
            return False
        
        value = annotation.value
        
        if self._annotation_values_regexp.match(value) is not None:
            
            samples = self._get_output_samples(clip)
            
            if samples is not None:
                
                # Create dataset from clip samples.
                name = '/clips/{:08d}'.format(clip.id)
                self._file[name] = samples
                
                # Set dataset attributes from clip metadata.
                attrs = self._file[name].attrs
                attrs['id'] = clip.id
                attrs['station'] = clip.station.name
                attrs['microphone'] = clip.mic_output.device.model.name
                attrs['detector'] = clip.creating_processor.name
                attrs['night'] = str(clip.date)
                attrs['start_time'] = _format_datetime(clip.start_time)
                attrs['original_sample_rate'] = clip.sample_rate
                attrs['classification'] = value
    
                return True
            
            else:
                return False
        
        else:
            return False
        
        
    def _get_output_samples(self, clip):
        
        samples = clip.sound.samples
        sample_rate = clip.sound.sample_rate
        
        min_clip_length = self._get_min_clip_length(sample_rate)
        
        if len(samples) >= min_clip_length:
            # clip long enough
            
            if sample_rate != _OUTPUT_CLIP_SAMPLE_RATE:
                # clip not at output sample rate
                
                samples = resampy.resample(
                    samples[:min_clip_length], sample_rate,
                    _OUTPUT_CLIP_SAMPLE_RATE)
                
            return samples[:self._output_clip_length]
        
        else:
            # clip too short
            
            return None
        
        
    def _get_min_clip_length(self, sample_rate):
        
        try:
            return self._min_clip_lengths[sample_rate]
        
        except KeyError:
            # don't yet have minimum clip length for this sample rate
            
            n = signal_utils.seconds_to_frames(
                self._output_clip_duration, sample_rate)
            
            while True:
                
                x = np.zeros(n)
                y = resampy.resample(x, sample_rate, _OUTPUT_CLIP_SAMPLE_RATE)
                
                if len(y) >= self._output_clip_length:
                    break
                
                else:
                    # `n` samples at `sample_rate` resample to fewer than
                    # `_OUTPUT_CLIP_LENGTH` samples at
                    # `_OUTPUT_CLIP_SAMPLE_RATE`
                    
                    n += 1
                    
            # Cache computed length.
            self._min_clip_lengths[sample_rate] = n
            
            return n
            
        
    def end_exports(self):
        self._file['/clips'].attrs['sample_rate'] = _OUTPUT_CLIP_SAMPLE_RATE
    

def _format_datetime(dt):
    return dt.strftime(_START_TIME_FORMAT)

