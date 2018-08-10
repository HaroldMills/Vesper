"""Module containing class `ClassifierTrainingClipsExporter`."""


import logging

import h5py
import numpy as np
import resampy

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
import vesper.command.command_utils as command_utils
import vesper.django.app.annotation_utils as annotation_utils
import vesper.util.signal_utils as signal_utils


# TODO: Make detector name and output sample rate command arguments.


# Settings for 2017 coarse classification examples export.
_DETECTOR_NAME = 'Thrush'
_CLASSIFICATION_ANNOTATION_NAME = 'Classification'
_CLASSIFICATIONS = ['Call*', 'Noise']
_OTHER_ANNOTATION_NAMES = []
_DEFAULT_ANNOTATION_VALUES = {}
_OUTPUT_CLIP_MODE = 'Initial'
_OUTPUT_CLIP_DURATIONS = {
    'Tseep': .236,    # 3000 / 22050 + .1
    'Thrush': .326    # 5000 / 22050 + .1
}
_OUTPUT_CLIP_SAMPLE_RATE = 22050
_START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


# Settings for 2018 detector training.
# _DETECTOR_NAME = 'Tseep'
# _CLASSIFICATION_ANNOTATION_NAME = 'Classification'
# _CLASSIFICATIONS = ['Call*', 'Noise']
# _OTHER_ANNOTATION_NAMES = ['Call Center Index', 'Call Center Freq']
# _DEFAULT_ANNOTATION_VALUES = {
#     'Call Center Index': 0,
#     'Call Center Freq': 0
# }
# _OUTPUT_CLIP_MODE = 'Center'
# _OUTPUT_CLIP_DURATIONS = {
#     'Tseep': 1,
#     'Thrush': 1
# }
# _OUTPUT_CLIP_SAMPLE_RATE = 24000
# _START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


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
    
        self._output_clip_duration = _OUTPUT_CLIP_DURATIONS[_DETECTOR_NAME]
            
        self._output_clip_length = signal_utils.seconds_to_frames(
            self._output_clip_duration, _OUTPUT_CLIP_SAMPLE_RATE)

        self._min_clip_lengths = {
            _OUTPUT_CLIP_SAMPLE_RATE: self._output_clip_length
        }
        
    
    def export(self, clip):
        
        classification = self._get_annotation_value(
            clip, _CLASSIFICATION_ANNOTATION_NAME)
        
        if classification is not None and \
                self._classifications_regexp.match(classification) is not None:
            
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
            
            
    def _get_output_samples(self, clip):
        
        samples = clip.audio.samples
        sample_rate = clip.audio.sample_rate
        
        min_clip_length = self._get_min_clip_length(sample_rate)
        
        if len(samples) >= min_clip_length:
            # clip long enough
            
            if sample_rate != _OUTPUT_CLIP_SAMPLE_RATE:
                # clip not at output sample rate
                
                samples = resampy.resample(
                    samples[:min_clip_length], sample_rate,
                    _OUTPUT_CLIP_SAMPLE_RATE)
                
            if _OUTPUT_CLIP_MODE == 'Initial':
                return self._get_output_samples_initial(samples)
            
            else:
                return self._get_output_samples_center(samples)
        
        else:
            # clip too short
            
            return None
        
        
    def _get_output_samples_initial(self, samples):
        return samples[:self._output_clip_length]
    
    
    def _get_output_samples_center(self, samples):
        offset = (len(samples) - self._output_clip_length) // 2
        return samples[offset:offset + self._output_clip_length]

    
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
