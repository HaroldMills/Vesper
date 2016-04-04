"""Module containing class `ClipSegmentsExporter`."""


import datetime
import logging
import os.path
import random

import h5py

from vesper.vcl.clip_visitor import ClipVisitor
from vesper.vcl.command import CommandSyntaxError
import vesper.util.nfc_coarse_classifier as nfc_coarse_classifier
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Exports clip segments of a specified duration to an HDF5 file.

The clips from which segments are exported can be limited by the
clip query arguments. The portion of clips from which segments are
exported can be specified with the --segment-source argument.
'''.strip()


# TODO: Support arguments with restricted value sets, e.g. enumerations.
# TODO: Support conditionally required arguments, e.g. when another
# argument has a certain value.


_SEGMENT_SOURCES = frozenset([
    nfc_coarse_classifier.SEGMENT_SOURCE_CLIP,
    nfc_coarse_classifier.SEGMENT_SOURCE_CLIP_CENTER,
    nfc_coarse_classifier.SEGMENT_SOURCE_SELECTION])


_ARGS = '''

- name: --output-file
  required: true
  value description: output file path
  
- name: --segment-source
  required: true
  value description: Clip, Clip Center, or Selection
  documentation: |
      The source of the segments to export. The location of the segment
      within the source is chosen at random according to a uniform
      distribution.
      Values:
          clip
              the entire clip.
          clip center
              the center portion of the clip, with duration equal to
              --source-width. If the clip is shorter than --source-width,
              no segment is exported.
          selection
              the selected portion of the clip. If a clip has no selection
              or the selection is shorter than --segment-duration, no
              segment is exported.
              
  
- name: --source-width
  required: optional
  value description: seconds
  documentation: |
    The width of the center portion of the clip from which to export
    a segment.
    Dependency: --segment-source "clip center".

- name: --segment-duration
  required: true
  value description: seconds
  
'''


class ClipSegmentsExporter(object):


    name = 'Clip Segments'
    
        
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(ClipSegmentsExporter.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(ClipSegmentsExporter, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def export(self):
        self._clip_visitor.visit_clips()
        return True
        
        
class _ClipVisitor(ClipVisitor):
    
    
    arg_descriptors = \
        vcl_utils.parse_command_args_yaml(_ARGS) + \
        ClipVisitor.arg_descriptors


    def __init__(self, positional_args, keyword_args):
        
        super(_ClipVisitor, self).__init__(positional_args, keyword_args)
        
        self._file_path = vcl_utils.get_required_keyword_arg(
            'output-file', keyword_args)
            
        self._segment_source = vcl_utils.get_required_keyword_arg(
            'segment-source', keyword_args)
        
        _check_segment_source(self._segment_source)
        
        if self._segment_source == \
                nfc_coarse_classifier.SEGMENT_SOURCE_CLIP_CENTER:
            
            self._source_duration = float(
                vcl_utils.get_required_keyword_arg(
                    'source-duration', keyword_args))
            
        else:
            self._source_duration = None
            
        self._segment_dur = float(
            vcl_utils.get_required_keyword_arg(
                'segment-duration', keyword_args))
        

    def begin_visits(self):
        
        # It is important to provide the random number generator with
        # the same seed each time this method runs, so that this script
        # will output the same segments for the same input each time it
        # runs.
        random.seed(0)
        
        self._clip_count = 0
        self._segment_count = 0
        self._short_clips = []
        
        self._file = h5py.File(self._file_path, 'w')
        
        
    def visit(self, clip):
        
        segment = nfc_coarse_classifier.extract_clip_segment(
            clip, self._segment_dur, self._segment_source,
            self._source_duration)
        
        if segment is None:
            # source not long enough to extract segment from
                
            self._short_clips.append(clip)
            
        else:
            
            # Write samples to HDF5 file.
            dataset_name = _create_clip_dataset_name(
                clip, segment.start_index)
            self._file[dataset_name] = segment.samples
            
            # Set call segment attributes in HDF5 file.
            attrs = self._file[dataset_name].attrs
            attrs['station_name'] = clip.station.name
            attrs['detector_name'] = clip.detector_name
            attrs['clip_start_time'] = str(clip.start_time)
            attrs['sample_rate'] = clip.sound.sample_rate
            attrs['segment_start_index'] = segment.start_index
            attrs['classification'] = \
                _get_hdf5_clip_class_name(clip.clip_class_name)
            
            self._segment_count += 1

    
    def end_visits(self):
        self._file.close()
        logging.info(
            'Extracted {} segments from {} clips.'.format(
                  self._segment_count, self._clip_count))
        self._log_short_clips()
        # _show_hdf5_file(self._file_path)
        
        
    def _log_short_clips(self):
        n = len(self._short_clips)
        if n != 0:
            logging.info((
                'The following {} clips were too short to extract '
                'segments from:').format(n))
            for clip in self._short_clips:
                file_name = os.path.basename(clip.file_path)
                start_index, length = clip.selection
                logging.info('    {} ({}, {})'.format(
                    file_name, start_index, length))


def _check_segment_source(source):
    if source not in _SEGMENT_SOURCES:
        raise CommandSyntaxError(
            'Unrecognized segment source "{}".'.format(source))
        
        
def _create_clip_dataset_name(clip, segment_start_index):
    
    dt = clip.start_time
    
    # Round dt to nearest millisecond.
    milliseconds = int(round(dt.microsecond / 1000.))
    dt = dt.replace(microsecond=0)
    dt += datetime.timedelta(milliseconds=milliseconds)
    
    # Format date.
    date = dt.date().strftime('%Y-%m-%d')
    
    # Format time.
    time = dt.time().strftime('%H:%M:%S')
    millisecond = int(round(dt.microsecond / 1000.))
    time += '.{:03d}'.format(millisecond)
    
    return '_'.join([
        clip.station.name, clip.detector_name, date, time,
        str(segment_start_index)])


def _get_hdf5_clip_class_name(name):
    return name if name is not None else ''


def _show_hdf5_file(file_path):
    
    try:
        file_ = h5py.File(file_path, 'r')
        
    except IOError:
        pass
    
    else:
        
        print('segments:')
        
        for name in file_:
            s = file_[name]
            print('   ', name, s.shape)
            for name, value in s.attrs.items():
                print('       ', name + ':', value)
        
        file_.close()
