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


class TagClipsCommand(ClipSetCommand):
    
    
    extension_name = 'tag_clips'
    
    
    def __init__(self, args):
        
        super().__init__(args, True)
        
        get_opt = command_utils.get_optional_arg
        self._clip_count = get_opt('clip_count', args)
        
        
    def execute(self, job_info):
        self._job_info = job_info
        clip_indices = self._get_tag_clip_indices()
        self._tag_clips(clip_indices)
        return True
    
    
    def _get_tag_clip_indices(self):
        
        if self._clip_count is None:
            # tag all clips

            return None
            
        clip_count = self._count_clips()
        
        if clip_count <= self._clip_count:
            # tag all clips
            
            return None

        # If we get here, a clip count is specified and it is less than
        # the number of untagged clips.
            
        _logger.info('Getting indices of clips to tag...')
        
        indices = random.sample(range(clip_count), self._clip_count)
            
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
                tag_excluded=True,
                order=False)
            
            count += clips.count()
            
        return count
            

    def _tag_clips(self, clip_indices):
        
        start_time = time.time()
        
        value_tuples = self._create_clip_query_values_iterator()
        
        clip_index = 0
        total_clip_count = 0
        total_tagged_count = 0
        
        for station, mic_output, date, detector in value_tuples:
            
            # Get clip for this station, mic_output, date, and detector.
            clips = model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                date=date,
                detector=detector,
                annotation_name=self._annotation_name,
                annotation_value=self._annotation_value,
                tag_name=self._tag_name,
                tag_excluded=True,
                order=False)

            # Get list of clip IDs.
            clip_ids = clips.values_list('pk', flat=True)
            
            # Get IDs of clips to tag.
            tag_clip_ids = \
                self._get_tag_clip_ids(clip_ids, clip_index, clip_indices)
            clip_count = len(clip_ids)
            tagged_count = len(tag_clip_ids)
            clip_index += clip_count
                
            # Tag clips.
            try:
                self._tag_clip_batch(tag_clip_ids)
            except Exception as e:
                batch_text = \
                    _get_batch_text(station, mic_output, date, detector)
                command_utils.log_and_reraise_fatal_exception(
                    e, f'Tagging of clips for {batch_text}')

            # Log clip counts.
            if tagged_count == clip_count:
                prefix = 'Tagged'
            else:
                untagged_count = clip_count - tagged_count
                prefix = (
                    f'Tagged {tagged_count} and left untagged '
                    f'{untagged_count} of')
            count_text = text_utils.create_count_text(clip_count, 'clip')
            batch_text = _get_batch_text(station, mic_output, date, detector)
            _logger.info(f'{prefix} {count_text} for {batch_text}.')

            total_clip_count += clip_count
            total_tagged_count += tagged_count
                
        # Log total clip counts and tagging rate.
        if total_tagged_count == total_clip_count:
            prefix = 'Tagged'
        else:
            total_untagged_count = total_clip_count - total_tagged_count
            prefix = (
                f'Tagged {total_tagged_count} and left untagged '
                f'{total_untagged_count} of')
        count_text = text_utils.create_count_text(total_clip_count, 'clip')
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_clip_count, 'clips')
        _logger.info(f'{prefix} a total of {count_text}{timing_text}.')


    def _get_tag_clip_ids(self, clip_ids, start_clip_index, clip_indices):

        if clip_indices is None:
            # tagging all clips

            return clip_ids

        else:
            # not tagging all clips

            clip_index = start_clip_index
            tag_clip_ids = []
        
            for clip_id in clip_ids:
                
                if clip_index in clip_indices:
                    tag_clip_ids.append(clip_id)
                    
                clip_index += 1

            return tag_clip_ids


    def _tag_clip_batch(self, clip_ids):
        
        with archive_lock.atomic():
             
            with transaction.atomic():
            
                # See note in untag_clips_command.py about maximum
                # chunk size. I'm not certain we have to do the same
                # thing here, but it seems likely that we do, for a
                # similar reason.
                max_chunk_size = 900
                
                tag_info = TagInfo.objects.get(name=self._tag_name)
                action = TagEdit.ACTION_SET
                creation_time = time_utils.get_utc_now()
                creating_job = Job.objects.get(id=self._job_info.job_id)
                
                for i in range(0, len(clip_ids), max_chunk_size):
                    
                    chunk = clip_ids[i:i + max_chunk_size]
                    
                    # Create tags.
                    Tag.objects.bulk_create([
                        Tag(
                            clip_id=clip_id,
                            info=tag_info,
                            creation_time=creation_time,
                            creating_user=None,
                            creating_job=creating_job,
                            creating_processor=None)
                        for clip_id in chunk])
                    
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
