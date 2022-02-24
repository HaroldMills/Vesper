"""Module containing class `UntagClipsCommand`."""


import logging
import random
import time

from django.db import transaction

from vesper.command.clip_set_command import ClipSetCommand
from vesper.django.app.models import Job, Tag, TagEdit, TagInfo
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils


_logger = logging.getLogger()


class UntagClipsCommand(ClipSetCommand):
    
    
    extension_name = 'untag_clips'
    
    
    def __init__(self, args):
        
        super().__init__(args, True)
        
        get_opt = command_utils.get_optional_arg
        self._retain_count = get_opt('retain_count', args)
        
        
    def execute(self, job_info):
        self._job_info = job_info
        clip_indices = self._get_retain_clip_indices()
        if clip_indices is not None:
            self._untag_clips(clip_indices)
        return True
    
    
    def _get_retain_clip_indices(self):
        
        if self._retain_count is None or self._retain_count == 0:
            # retain no clips

            return []
            
        # Count clips that are candidates for untagging.
        clip_count = self._count_clips()
        
        if clip_count <= self._retain_count:
            # retain all clips
            
            _logger.info(
                f'Retain count {self._retain_count} is greater than '
                f'or equal to number of specified clips {clip_count}, '
                f'so no clips will be untagged.')
            
            # We use a return value of `None` to inform the caller
            # that there's nothing to do.
            return None

        # If we get here, a nonzero retain count is specified that is less
        # than the number of clips that are candidates for untagging.
            
        _logger.info('Selecting clips for which to retain tags...')
        
        indices = random.sample(range(clip_count), self._retain_count)
            
        return frozenset(indices)
 
 
    def _count_clips(self):
        
        value_tuples = self._create_clip_query_values_iterator()
        count = 0
        
        for station, mic_output, date, detector in value_tuples:
            
            clips = model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                date=date,
                detector=detector,
                annotation_name=self._annotation_name,
                annotation_value=self._annotation_value,
                tag_name=self._tag_name,
                order=False)
            
            count += clips.count()
            
        return count
            

    def _untag_clips(self, retain_indices):
        
        start_time = time.time()
        
        value_tuples = self._create_clip_query_values_iterator()
        
        clip_index = 0
        total_clip_count = 0
        total_untagged_count = 0
        
        for station, mic_output, date, detector in value_tuples:
            
            # Get clips for this station, mic_output, date, and detector
            clips = model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                date=date,
                detector=detector,
                annotation_name=self._annotation_name,
                annotation_value=self._annotation_value,
                tag_name=self._tag_name,
                order=False)
            
            # Get list of clip IDs.
            clip_ids = clips.values_list('pk', flat=True)

            # Get IDs of clips to untag.
            untag_clip_ids = \
                self._get_untag_clip_ids(clip_ids, clip_index, retain_indices)
            clip_count = len(clip_ids)
            untagged_count = len(untag_clip_ids)
            clip_index += clip_count
              
            # Untag clips.
            try:
                self._untag_clip_batch(untag_clip_ids)
            except Exception as e:
                batch_text = \
                    _get_batch_text(station, mic_output, date, detector)
                command_utils.log_and_reraise_fatal_exception(
                    e, f'Untagging of clips for {batch_text}')

            # Log clip counts.
            if untagged_count == clip_count:
                prefix = 'Untagged'
            else:
                retained_count = clip_count - untagged_count
                prefix = (
                    f'Untagged {untagged_count} and left tagged '
                    f'{retained_count} of')
            count_text = text_utils.create_count_text(clip_count, 'clip')
            batch_text = _get_batch_text(station, mic_output, date, detector)
            _logger.info(f'{prefix} {count_text} for {batch_text}.')

            total_clip_count += clip_count
            total_untagged_count += untagged_count
                
        # Log total clip counts and untagging rate.
        if total_untagged_count == total_clip_count:
            prefix = 'Untagged'
        else:
            total_retained_count = total_clip_count - total_untagged_count
            prefix = (
                f'Untagged {total_untagged_count} and left tagged '
                f'{total_retained_count} of')
        count_text = text_utils.create_count_text(total_clip_count, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_clip_count, 'clips')
        _logger.info(f'{prefix} a total of {count_text}{timing_text}.')


    def _get_untag_clip_ids(self, clip_ids, start_clip_index, retain_indices):

        if len(retain_indices) == 0:
            # untagging all clips

            return clip_ids

        else:
            # not untagging all clips

            clip_index = start_clip_index
            untag_clip_ids = []
        
            for clip_id in clip_ids:
                
                if clip_index not in retain_indices:
                    untag_clip_ids.append(clip_id)
                    
                clip_index += 1

            return untag_clip_ids


    def _untag_clip_batch(self, clip_ids):
        
        with archive_lock.atomic():
             
            with transaction.atomic():
            
                # Untag clips in chunks to limit the number of clip IDs
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
                
                tag_info = TagInfo.objects.get(name=self._tag_name)
                action = TagEdit.ACTION_DELETE
                creation_time = time_utils.get_utc_now()
                creating_job = Job.objects.get(id=self._job_info.job_id)
                
                for i in range(0, len(clip_ids), max_chunk_size):
                    
                    chunk = clip_ids[i:i + max_chunk_size]
                    
                    # Delete tags.
                    Tag.objects.filter(info=tag_info, clip_id__in=chunk).delete()
                    
                    # Create tag edits.
                    TagEdit.objects.bulk_create([
                        TagEdit(
                            clip_id=clip_id,
                            info=tag_info,
                            action=action,
                            creation_time=creation_time,
                            creating_user=None,
                            creating_job=creating_job,
                            creating_processor=None)
                        for clip_id in chunk])
                    
                    
def _get_batch_text(station, mic_output, date, detector):
    return (
        f'station "{station.name}", mic output "{mic_output.name}", '
        f'date {date}, and detector "{detector.name}"')
