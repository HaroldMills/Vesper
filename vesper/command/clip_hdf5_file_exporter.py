"""Module containing class `ClipHdf5FileExporter`."""


import logging
import os

import h5py

from vesper.command.clip_exporter import ClipExporter
from vesper.command.command import CommandExecutionError
from vesper.singleton.archive import archive
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.preset_manager import preset_manager
from vesper.util.bunch import Bunch
import vesper.util.clip_time_interval_utils as clip_time_interval_utils
import vesper.util.os_utils as os_utils
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

_SINGLE_OUTPUT_MIC_NAME_SUFFIX = ' Output'


_logger = logging.getLogger()


class ClipHdf5FileExporter(ClipExporter):
    
    """Exports clips to one or more HDF5 files."""
        
    
    extension_name = 'Clip HDF5 File Exporter'

    clip_query_set_select_related_args = (
        'station', 'mic_output__device', 'mic_output__model_output',
        'creating_processor'
    )


    def __init__(self, args):

        get = command_utils.get_required_arg
        self._settings_preset_name = \
            get('clip_hdf5_file_export_settings_preset', args)
        self._export_to_multiple_files = get('export_to_multiple_files', args)
        self._output_path = get('output_path', args)
    
        self._time_interval = \
            _parse_settings_preset(self._settings_preset_name)


    def begin_exports(self):
        if not self._export_to_multiple_files:
            self._create_hdf5_file(self._output_path)


    def _create_hdf5_file(self, file_path):

        # Create parent directory if needed.
        dir_path = os.path.dirname(file_path)
        try:
            os_utils.create_directory(dir_path)
        except OSError as e:
            raise CommandExecutionError(str(e))

        # Create HDF5 file.
        try:
            self._file = h5py.File(file_path, 'w')
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        # Always create "clips" group in file, even if it will be empty.
        self._file.create_group('/clips')
        
    
    def begin_subset_exports(
            self, station, mic_output, date, detector, clip_count):

        if self._export_to_multiple_files:

            if clip_count != 0:
                # have clips to export

                file_name = \
                    _create_hdf5_file_name(station, mic_output, date, detector)

                file_path = os.path.join(self._output_path, file_name)

                self._create_hdf5_file(file_path)

            else:
                # no clips to export

                self._file = None


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


    def end_subset_exports(self):
        if self._export_to_multiple_files and self._file is not None:
            self._file.close()


    def end_exports(self):
        if not self._export_to_multiple_files:
            self._file.close()


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
    

def _create_hdf5_file_name(station, mic_output, date, detector):

    # Abbreviate mic output name if mic has only one output.
    mic_name = mic_output.name
    if mic_name.endswith(_SINGLE_OUTPUT_MIC_NAME_SUFFIX):
        mic_name = mic_name[:-len(_SINGLE_OUTPUT_MIC_NAME_SUFFIX)]

    return f'{station.name}_{mic_name}_{detector.name}_{date}.h5'


def _get_annotations(clip):
    annotations = clip.string_annotations.select_related('info')
    return dict((a.info.name, a.value) for a in annotations)
        
        
def _format_start_time(dt):
    return dt.strftime(_START_TIME_FORMAT)
