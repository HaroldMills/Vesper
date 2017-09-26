"""Module containing class `DeleteClipsCommand`."""


import logging
import random

from django.db import transaction

from vesper.command.command import Command
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.os_utils as os_utils


_logger = logging.getLogger()


class DeleteClipsCommand(Command):
    
    
    extension_name = 'delete_clips'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._classification = get('classification', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._retain_count = get('retain_count', args)
        
        
    def execute(self, job_info):
        
        self._job_info = job_info

        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                self._classification, 'Classification', 'Unclassified')

        retain_indices = self._get_retain_clip_indices()
        
        self._delete_clips(retain_indices)
        
        return True
    
    
    def _get_retain_clip_indices(self):
        
        if self._retain_count == 0:
            indices = []
            
        else:
            
            _logger.info('Getting indices of clips to retain...')
            
            clip_count = self._count_clips()
            
            if clip_count <= self._retain_count:
                # will retain all clips
                
                indices = list(range(clip_count))
                
            else:
                # will not retain all clips
                
                indices = random.sample(range(clip_count), self._retain_count)
            
        return frozenset(indices)
    
    
    def _count_clips(self):
        
        value_tuples = self._create_clip_query_values_iterator()
        count = 0
        
        for detector, station, mic_output, date in value_tuples:
            
            clips = model_utils.get_clips(
                station, mic_output, detector, date, self._annotation_name,
                self._annotation_value, order=False)
            
            count += clips.count()
            
        return count
            

    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._detector_names, self._sm_pair_ui_names,
                self._start_date, self._end_date)
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction',
                'The archive was not modified.')

    
    def _delete_clips(self, retain_indices):
        
        value_tuples = self._create_clip_query_values_iterator()
        
        index = 0
        total_retained_count = 0
        
        for detector, station, mic_output, date in value_tuples:
            
            clips = model_utils.get_clips(
                station, mic_output, detector, date, self._annotation_name,
                self._annotation_value, order=False)
            
            count = 0
            retained_count = 0
            
            for clip in clips:
                
                if index not in retain_indices:
                    self._delete_clip(clip)
                else:
                    retained_count += 1
                    
                count += 1
                index += 1
                
            deleted_count = count - retained_count
            count_text = _create_clip_count_text(count)
            _logger.info((
                'Deleted {} and retained {} of {} for detector "{}", '
                'station "{}", mic output "{}", and date {}.').format(
                    deleted_count, retained_count, count_text,
                    detector.name, station.name, mic_output.name, date))

            total_retained_count += retained_count
                
        deleted_count = index - total_retained_count
        count_text = _create_clip_count_text(index)
        _logger.info(
            'Deleted {} and retained {} of a total of {}.'.format(
                deleted_count, total_retained_count, count_text))


    def _delete_clip(self, clip):
        
        try:
            
            with archive_lock.atomic():
                 
                with transaction.atomic():
                 
                    file_path = clip.wav_file_path
                    if file_path is not None:
                        os_utils.delete_file(file_path)
                     
                    clip.delete()
                    
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Deletion of clip "{}"'.format(str(clip)),
                'The clip and associated annotations were not modified.')
        

def _create_clip_count_text(count):
    suffix = '' if count == 1 else 's'
    return '{} clip{}'.format(count, suffix)
