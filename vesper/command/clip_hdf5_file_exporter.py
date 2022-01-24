"""Module containing class `ClipHdf5FileExporter`."""


import logging

import h5py

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import StringAnnotation
from vesper.singleton.archive import archive
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.preset_manager import preset_manager
from vesper.util.bunch import Bunch
import vesper.util.clip_time_interval_utils as clip_time_interval_utils
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
# _EXTRACTION_START_OFFSETS = {
#     'Tseep': -.5,
#     'Thrush': -.5
# }
# _EXTRACTION_DURATIONS = {
#     'Tseep': 1.2,
#     'Thrush': 1.2
# }
# _ANNOTATION_INFOS = [
#     ('Classification', None), 
#     ('Call Start Index', int), 
#     ('Call End Index', int)]
# _DEFAULT_ANNOTATION_VALUES = {}
# _START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


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


# Settings for positive examples from PSW NOGO Archive 2 for NOGO coarse
# classifier training.
# _EXTRACTION_START_OFFSETS = {
#     'NOGO': -.2
# }
# _EXTRACTION_DURATIONS = {
#     'NOGO': .6
# }
# _ANNOTATION_INFOS = [
#     ('Classification', None), 
#     ('Call Start Index', int)
# ]
# _DEFAULT_ANNOTATION_VALUES = {}


# Settings for negative examples from PSW NOGO Archive 2 for NOGO coarse
# classifier training.
# _EXTRACTION_START_OFFSETS = {
#     'NOGO': 0
# }
# _EXTRACTION_DURATIONS = {
#     'NOGO': .6
# }
# _ANNOTATION_INFOS = [
#     ('Classification', None), 
# ]
# _DEFAULT_ANNOTATION_VALUES = {
#     'Classification': 'Other',
# }


_DEFAULT_TIME_INTERVAL = Bunch(
    left_padding=0,
    right_padding=0,
    offset=0)

_START_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


_logger = logging.getLogger()


class ClipHdf5FileExporter:
    
    """
    Exports clips to an HDF5 file.
    
    The clips are written to the server-side HDF5 file specified in
    the `output_file_path` argument.
    """
        
    
    extension_name = 'Clip HDF5 File Exporter'
    
    
    def __init__(self, args):

        get = command_utils.get_required_arg
        self._settings_preset_name = \
            get('clip_hdf5_file_export_settings_preset', args)
        self._output_file_path = get('output_file_path', args)
    
        self._time_interval = \
            _parse_settings_preset(self._settings_preset_name)


    def begin_exports(self):
        
        try:
            self._file = h5py.File(self._output_file_path, 'w')
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        # Always create the "clips" group, even if it will be empty.
        self._file.create_group('/clips')
        
    
    def export(self, clip):
        
        annotations = _get_annotations(clip)

        try:
            samples, start_index = self._get_samples(clip, annotations)
        except Exception as e:
            _logger.warning(
                f'Could not get samples for clip {clip}, so it will '
                f'not appear in output. Error message was: {e}')
            return False

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
        attrs['clip_start_time'] = _format_start_time(clip.start_time)
        attrs['clip_start_index'] = clip.start_index
        attrs['clip_length'] = clip.length
        attrs['export_start_index'] = start_index
        
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
        
 
    def _get_samples(self, clip, annotations):
        
        start_offset, length = \
            clip_time_interval_utils.get_clip_time_interval(
                clip, self._time_interval)

        # TODO: Specify in settings whether or not start offset is
        # relative to an annotation value, and if so which one.
        #
        # If "Call Start Index" annotation is present, assume extraction
        # start index is specified relative to it, and modify start
        # offset to be relative to clip start index rather than call
        # start index.
        # call_start_index = annotations.get('Call Start Index')
        # if call_start_index is not None:
        #     start_offset += call_start_index - clip.start_index

        samples = clip_manager.get_samples(clip, start_offset, length)
        
        start_index = clip.start_index + start_offset
        
        return samples, start_index
    

    def end_exports(self):
        pass


def _parse_settings_preset(preset_name):
    
    if preset_name == archive.NULL_CHOICE:
        # no preset specified

        return _DEFAULT_TIME_INTERVAL
    
    preset_type = 'Clip HDF5 File Export Settings'
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
    

def _get_annotations(clip):
    annotations = clip.string_annotations.select_related('info')
    return dict((a.info.name, a.value) for a in annotations)
        
        
def _format_start_time(dt):
    return dt.strftime(_START_TIME_FORMAT)
