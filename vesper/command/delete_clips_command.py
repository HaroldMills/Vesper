"""Module containing class `DeleteClipsCommand`."""


import logging
import random
import time

from django.db import transaction

from vesper.command.command import Command
from vesper.django.app.models import Clip
from vesper.singletons import clip_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.text_utils as text_utils


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
                'Classification', self._classification)

        retain_indices = self._get_retain_clip_indices()
        
        self._clip_manager = clip_manager.instance
        
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
        
        start_time = time.time()
        
        retaining_clips = len(retain_indices) == 0
        
        value_tuples = self._create_clip_query_values_iterator()
        
        index = 0
        total_retained_count = 0
        
        for detector, station, mic_output, date in value_tuples:
            
            # Get clips for this detector, station, mic_output, and date
            clips = model_utils.get_clips(
                station, mic_output, detector, date, self._annotation_name,
                self._annotation_value, order=False)
            
            
            # Figure out which clips should be deleted.
            
            count = 0
            retained_count = 0
            clips_to_delete = []
            
            for clip in clips:
                
                if index not in retain_indices:
                    clips_to_delete.append(clip)
                else:
                    retained_count += 1
                    
                count += 1
                index += 1
                
                
            # Delete clips.
            try:
                self._delete_clip_batch(clips_to_delete)
            except Exception as e:
                batch_text = \
                    _get_batch_text(detector, station, mic_output, date)
                command_utils.log_and_reraise_fatal_exception(
                    e, 'Deletion of clips for {}'.format(batch_text))

            # Log deletions.
            if retaining_clips:
                prefix = 'Deleted'
            else:
                deleted_count = count - retained_count
                prefix = 'Deleted {} and retained {} of'.format(
                    deleted_count, retained_count)
            count_text = text_utils.create_count_text(count, 'clip')
            batch_text = _get_batch_text(detector, station, mic_output, date)
            _logger.info(
                '{} {} for {}.'.format(prefix, count_text, batch_text))

            total_retained_count += retained_count
                
        # Log total deletions and deletion rate.
        if total_retained_count == 0:
            prefix = 'Deleted'
        else:
            deleted_count = index - total_retained_count
            prefix = 'Deleted {} and retained {} of'.format(
                deleted_count, total_retained_count)
        count_text = text_utils.create_count_text(index, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, index, 'clips')
        _logger.info('{} a total of {}{}.'.format(
            prefix, count_text, timing_text))


    def _delete_clip_batch(self, clips):
        
        with archive_lock.atomic():
             
            with transaction.atomic():
            
                # Delete clips in chunks to limit the number of clip IDs
                # we pass to `Clip.objects.filter`.
                
                # Setting this too large can result in a
                # django.db.utils.OperationalError exception with the
                # message "too many SQL variables". We have seen this
                # happen with a maximum chunk size of 1000 on Windows,
                # though not on macOS. The web page
                # https://stackoverflow.com/questions/7106016/
                # too-many-sql-variables-error-in-django-witih-sqlite3
                # suggests that the maximum chunk size that will work
                # on Windows is somewhere between 900 and 1000, and
                # 900 seems to work.
                max_chunk_size = 900
                
                for i in range(0, len(clips), max_chunk_size):
                    
                    chunk = clips[i:i + max_chunk_size]
                    
                    # Delete clips from archive database.
                    ids = [clip.id for clip in chunk]
                    Clip.objects.filter(id__in=ids).delete()
                    
        # Delete clip audio files. We do this after the transaction so
        # that if the transaction fails, leaving the clips in the
        # database and raising an exception, we don't delete any clip
        # files.
        for clip in clips:
            self._clip_manager.delete_audio_file(clip)


def _get_batch_text(detector, station, mic_output, date):
    return \
        'detector "{}", station "{}", mic output "{}", and date {}'.format(
            detector.name, station.name, mic_output.name, date)
