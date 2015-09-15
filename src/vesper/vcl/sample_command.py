"""Module containing class `SampleCommand`."""


from __future__ import print_function

import logging
import random

from vesper.vcl.command import (
    Command, CommandExecutionError, CommandSyntaxError)
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
sample [<keyword arguments>]

Adds clips sampled from an input archive to an output archive.
'''.strip()
        

_ARGS = '''

- name: --output-archive
  required: true
  value description: directory path
  documentation: |
      The directory path of the output archive.
      The archive must already exist.
  
- name: --target-clip-count
  required: true
  value description: integer
  documentation: |
      The target number of clips in the output archive. The maximum
      number of clips taken from a single night will be limited if
      needed to yield a number of clips that is close to the target.
'''


class SampleCommand(Command):
    
    """
    vcl command that samples clips from an archive.
    
    Clips are sampled randomly from an input archive and written to
    an output archive. The number of clips that are output for any
    particular night is capped so that the total number of output
    clips is limited (approximately) to the specified target clip
    count.
    """
    
    
    name = 'sample'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        arg_descriptors = \
            vcl_utils.parse_command_args_yaml(_ARGS) + \
            vcl_utils.ARCHIVE_ARG_DESCRIPTORS + \
            vcl_utils.CLIP_QUERY_ARG_DESCRIPTORS
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return _HELP + '\n\n' + args_help
    
    
    def __init__(self, positional_args, keyword_args):
        
        super(SampleCommand, self).__init__()
        
        self._input_archive_dir_path = \
            vcl_utils.get_archive_dir_path(keyword_args)
            
        self._output_archive_dir_path = \
            vcl_utils.get_required_keyword_arg('output-archive', keyword_args)
            
        if self._output_archive_dir_path == self._input_archive_dir_path:
            raise CommandSyntaxError(
                'Input and output archive paths must differ.')
            
        self._target_clip_count = int(vcl_utils.get_required_keyword_arg(
            'target-clip-count', keyword_args))
        
        # TODO: Don't use `vcl_utils.get_clip_query` here since we require
        # exactly one detector and one clip class.
        (self._station_names, detector_names, clip_class_names,
         self._start_night, self._end_night) = \
            vcl_utils.get_clip_query(keyword_args)
            
        self._detector_name = self._get_name(
            detector_names, 'detectors', 'detector')
        
        self._clip_class_name = self._get_name(
            clip_class_names, 'clip-classes', 'clip class')
        
        
    def _get_name(self, names, arg_name, description):
        
        if names is None:
            raise CommandSyntaxError(
                'Required "--{}" argument is missing`'.format(arg_name))
            
        elif len(names) != 1:
            raise CommandSyntaxError(
                'Must specify exactly one {}.'.format(description))
        
        return names[0]
                
        
    def execute(self):
        
        self._input_archive = vcl_utils.open_archive(
            self._input_archive_dir_path)
        
        try:
            
            self._output_archive = vcl_utils.open_archive(
                self._output_archive_dir_path)
            
            try:
                
                logging.info('Computing maximum nightly clip count...')
                
                max_clip_count = self._get_max_clip_count(
                    self._target_clip_count)
                
                logging.info((
                    'Sampling input archive with a maximum nightly clip '
                    'count of {}...').format(max_clip_count))
                
                self._sample_clips(max_clip_count)
            
            finally:
                # TODO: Create a `vcl_utils` function for closing an archive?
                self._output_archive.close()
            
        finally:
            self._input_archive.close()
        
        return True

                
    def _get_max_clip_count(self, target_retained_clip_count):
        
        low = 0
        high = target_retained_clip_count
        
        # We assume that the target retained clip count is attainable,
        # i.e. that the archive contains more clips of the appropriate
        # class than requested. But perhaps we should verify this.
        
        # Invariant: Retained count is lower than target for max count
        # of `low`, and at least target for max count of `high`.
        
        while high != low + 1:
            
            mid = (high + low) // 2
            
            count = self._get_retained_clip_count(mid)
            
            if count >= target_retained_clip_count:
                high = mid
            else:
                low = mid
        
        return high
        
        
    def _get_retained_clip_count(self, max_night_count):
        
        retained_count = 0
        
        for station_name in self._station_names:
        
            counts = self._get_clip_counts(station_name)
                
            nights = counts.keys()
            nights.sort()
            
            for night in nights:
                
                count = counts[night]
                
                if count > max_night_count:
                    retained_count += max_night_count
                else:
                    retained_count += count
                    
        return retained_count
                
    
    def _get_clip_counts(self, station_name):
        
        try:
            return self._input_archive.get_clip_counts(
                station_name=station_name, detector_name=self._detector_name,
                clip_class_name=self._clip_class_name,
                start_night=self._start_night, end_night=self._end_night)
            
        except Exception as e:
            raise CommandExecutionError((
                'Could not get clip counts from archive "{}"'
                'for station "{}" and detector "{}". '
                'Error message was: {}').format(
                    self._input_archive_dir_path, station_name,
                    self._detector_name, str(e)))

    
    def _sample_clips(self, max_clip_count):
        
        for station_name in self._station_names:
        
            counts = self._get_clip_counts(station_name)
            
            nights = counts.keys()
            nights.sort()
            
            for night in nights:
                
                clips = self._input_archive.get_clips(
                    station_name, self._detector_name, night)
                
                n = len(clips)
                indices = xrange(n)
                if n > max_clip_count:
                    indices = random.sample(indices, max_clip_count)
                    n = max_clip_count
                    
                logging.info(
                    'Sampling {} clips for {}, {}, {}...'.format(
                        n, station_name, self._detector_name, night))
                
                for i in indices:
                    c = clips[i]
                    self._output_archive.add_clip(
                        c.station.name, c.detector_name, c.start_time, c.sound)
                    
