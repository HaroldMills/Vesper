"""Module containing class `CreateDatasetCallClipsCommand`."""


from datetime import timedelta as TimeDelta
import itertools
import logging
import time

from vesper.command.clip_set_command import ClipSetCommand
from vesper.django.app.models import (
    AnnotationInfo, Clip, Job, Processor, StringAnnotation,
    StringAnnotationEdit, Tag, TagEdit, TagInfo)
from vesper.singleton.archive import archive
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils


# TODO: Consider moving the `_ClipCreator` class to its own module.
# We use it in this class and in the noise clip creator. Also consider
# renaming the class to `BatchClipCreator`.


_PROCESSOR_NAME = 'Dataset Call Clip Creator 1.0'
_PROCESSOR_TYPE = 'Clip Creator'
_PROCESSOR_DESCRIPTION = '''
Processor created by Vesper's Create Dataset Call Clips command.
The Create Dataset Call Clips command assigns this processor as the
creating processor of each clip that it creates.
'''.lstrip()

_OLD_CLIP_ID_ANNO_NAME = 'Original Clip ID'
_OLD_CLIP_ID_ANNO_DESCRIPTION = '''
The ID of the clip from which the dataset clip was created.
'''.lstrip()

_NEW_CLIP_TAG_NAME = 'Dataset New'
_NEW_CLIP_TAG_DESCRIPTION = 'Tags a new dataset clip.'


_logger = logging.getLogger()


class CreateDatasetCallClipsCommand(ClipSetCommand):
    
    
    extension_name = 'create_dataset_call_clips'
    
    
    def __init__(self, args):

        super().__init__(args, True)

        self._clip_duration = \
            command_utils.get_required_arg('clip_duration', args)
        
        
    def execute(self, job_info):

        self._job_info = job_info

        job_start_time = time.time()

        # Get call start time annotation info ID.
        self._call_start_time_info_id = _get_anno_info_id('Call Start Time')
        if self._call_start_time_info_id is None:
            return False

        # Get call end time annotation info ID.
        self._call_end_time_info_id = _get_anno_info_id('Call End Time')
        if self._call_end_time_info_id is None:
            return False
        
        self._creation_time = time_utils.get_utc_now()
        self._creating_job = Job.objects.get(pk=self._job_info.job_id)
        self._creating_processor = _get_creating_processor()

        self._old_clip_id_anno_info = self._get_old_clip_id_anno_info()
        self._new_clip_tag_info = self._get_new_clip_tag_info()
        self._clip_creator = _ClipCreator()

        value_tuples = self._create_clip_query_values_iterator()

        total_old_clip_count = 0
        total_new_clip_count = 0
        
        for station, mic_output, date, detector in value_tuples:
            
            old_clips = model_utils.get_clips(
                station=station,
                mic_output=mic_output,
                date=date,
                detector=detector,
                annotation_name=self._annotation_name,
                annotation_value=self._annotation_value,
                tag_name=self._tag_name,
                order=False)
            
            old_clip_count = len(old_clips)
            new_clip_count = 0
            
            for old_clip in old_clips:
                if self._create_new_clip(old_clip):
                    new_clip_count += 1
                
            # Log file creations for this detector/station/mic_output/date.
            count_text = \
                text_utils.create_count_text(old_clip_count, 'clip')
            _logger.info(
                f'Created dataset call clips for {new_clip_count} of '
                f'{count_text} for station "{station.name}", mic output '
                f'"{mic_output.name}", date {date}, and detector '
                f'"{detector.name}".')
                
            total_old_clip_count += old_clip_count
            total_new_clip_count += new_clip_count
            
        # Make sure to create all clips.
        self._clip_creator.flush()

        # Log total clip creations and creation rate.
        count_text = \
            text_utils.create_count_text(total_new_clip_count, 'clip')
        elapsed_time = time.time() - job_start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_new_clip_count, 'clips')
        _logger.info(f'Created a total of {count_text}{timing_text}.')

        return True


    def _get_old_clip_id_anno_info(self):

        try:
            return AnnotationInfo.objects.get(name=_OLD_CLIP_ID_ANNO_NAME)
        except AnnotationInfo.DoesNotExist:
            return AnnotationInfo.objects.create(
                name=_OLD_CLIP_ID_ANNO_NAME,
                description=_OLD_CLIP_ID_ANNO_DESCRIPTION,
                type=AnnotationInfo.TYPE_STRING,
                creation_time=self._creation_time,
                creating_job=self._creating_job)

    
    def _get_new_clip_tag_info(self):

        try:
            return TagInfo.objects.get(name=_NEW_CLIP_TAG_NAME)
        except TagInfo.DoesNotExist:
            return TagInfo.objects.create(
                name=_NEW_CLIP_TAG_NAME,
                description=_NEW_CLIP_TAG_DESCRIPTION,
                creation_time=self._creation_time,
                creating_job=self._creating_job)


    def _create_new_clip(self, old_clip):

        new_clip = self._create_new_clip_aux(old_clip)

        if new_clip is None:
            return False

        else:
            new_annos = self._create_new_clip_annos(old_clip, new_clip)
            new_tags = self._create_new_clip_tags(old_clip, new_clip)
            self._clip_creator.add_clip(new_clip, new_annos, new_tags)
            return True


    def _create_new_clip_aux(self, old_clip):

        try:
            call_start_index, call_end_index = self._get_call_bounds(old_clip)
        except ValueError:
            return None

        # Get clip length.
        sample_rate = old_clip.sample_rate
        clip_length = int(round(self._clip_duration * sample_rate))

        # Get call length.
        call_length = call_end_index - call_start_index + 1

        if call_length > clip_length:
            # call longer than a dataset clip

            self._handle_clip_creation_error(
                old_clip, 'Call duration exceeds dataset clip duration')
            return None

        # Get recording length.
        channel = old_clip.recording_channel
        recording = channel.recording
        recording_length = recording.length

        if clip_length > recording_length:
            # recording is not long enough to hold a dataset clip

            self._handle_clip_creation_error(
                old_clip,
                'Dataset clip duration exceeds duration of recording')
            return None
        
        # Get new clip start index that centers call within clip.
        call_length = call_end_index - call_start_index
        offset = (clip_length - call_length) // 2
        clip_start_index = call_start_index - offset

        # Make sure clip would not overhang start of recording.
        if clip_start_index < 0:
            # clip would overhang start of recording

            self._handle_clip_creation_error(
                old_clip,
                'Dataset call clip would overhang start of recording')
            return None

        # Get new clip end index.
        clip_end_index = clip_start_index + clip_length - 1

        if clip_end_index >= recording_length:
            # clip would overhang end of recording

            self._handle_clip_creation_error(
                old_clip, 'Dataset call clip would overhang end of recording')
            return None

        # If we get here, the call fits within a dataset clip and a
        # dataset clip fits within the recording.

        # Get clip start time.
        start_offset = TimeDelta(seconds=clip_start_index / sample_rate)
        start_time = recording.start_time + start_offset

        # Get clip end time.
        end_offset = TimeDelta(seconds=clip_end_index / sample_rate)
        end_time = recording.start_time + end_offset

        # Create clip.
        return Clip(
            station=old_clip.station,
            mic_output=channel.mic_output,
            recording_channel=channel,
            start_index=clip_start_index,
            length=clip_length,
            sample_rate=sample_rate,
            start_time=start_time,
            end_time=end_time,
            date=old_clip.date,
            creation_time=self._creation_time,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)


    def _get_call_bounds(self, clip):

        call_start_index = self._get_call_bound(
            clip, self._call_start_time_info_id)
        
        call_end_index = self._get_call_bound(
            clip, self._call_end_time_info_id)

        return call_start_index, call_end_index


    def _get_call_bound(self, clip, info_id):
        
        try:
            anno = clip.string_annotations.get(info_id=info_id)
        except StringAnnotation.DoesNotExist:
            raise ValueError()

        return int(anno.value)


    def _handle_clip_creation_error(self, clip, message):
            _logger.warning(
                f'{message} for clip {str(clip)}. '
                f'No dataset call clip will be created for this clip.')

            
    def _create_new_clip_annos(self, old_clip, new_clip):

        # Copy old clip annotations for new clip.
        anno_copies = self._copy_annotations(old_clip, new_clip)

        # Get new clip annotation for old clip ID.
        new_anno = self._annotate_clip(
            new_clip, self._old_clip_id_anno_info, str(old_clip.id))

        # Get all annotations for new clip.
        return anno_copies + [new_anno]


    def _copy_annotations(self, old_clip, new_clip):
        return [
            self._annotate_clip(new_clip, a.info, a.value)
            for a in old_clip.string_annotations.all()]


    def _annotate_clip(self, clip, anno_info, anno_value):
        return StringAnnotation(
            clip=clip,
            info=anno_info,
            value=anno_value,
            creation_time=self._creation_time,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)


    def _create_new_clip_tags(self, old_clip, new_clip):

        # Copy old clip tags for new clip.
        tag_copies = self._copy_tags(old_clip, new_clip)

        # Get new dataset clip tag for new clip.
        new_tag = self._tag_clip(new_clip, self._new_clip_tag_info)
        
        # Get all tags for new clip.
        return tag_copies + [new_tag]


    def _copy_tags(self, old_clip, new_clip):
        return [
            self._tag_clip(new_clip, t.info)
            for t in old_clip.tags.all()]


    def _tag_clip(self, clip, tag_info):
        return Tag(
            clip=clip,
            info=tag_info,
            creation_time=self._creation_time,
            creating_job=self._creating_job,
            creating_processor=self._creating_processor)


def _get_anno_info_id(name):
    try:
        return AnnotationInfo.objects.get(name=name).id
    except AnnotationInfo.DoesNotExist:
        _logger.error(
            f'Required annotation info with name "{name}" is missing '
            f'from the archive database.')
        return None

    
def _get_creating_processor():

    try:
        processor = Processor.objects.get(
            name=_PROCESSOR_NAME, type=_PROCESSOR_TYPE)

    except Processor.DoesNotExist:

        _logger.info(f'Creating processor "{_PROCESSOR_NAME}"...')

        processor = Processor.objects.create(
            name=_PROCESSOR_NAME,
            type=_PROCESSOR_TYPE,
            description=_PROCESSOR_DESCRIPTION
        )

        archive.refresh_processor_cache()

    return processor


class _ClipCreator:


    def __init__(self, batch_size=50):
        self._batch_size = batch_size
        self._clips = []
        self._annos = []
        self._tags = []


    def add_clip(self, clip, annotations=None, tags=None):

        self._clips.append(clip)

        if annotations is not None:
            self._annos.append(annotations)

        if tags is not None:
            self._tags.append(tags)

        if len(self._clips) == self._batch_size:
            self.flush()


    def flush(self):

        if len(self._clips) != 0:
            # there are clips to create

            # Create clips.
            Clip.objects.bulk_create(self._clips)

            if len(self._annos) != 0:
                # there are annotations to create

                # Get list of annotations to create.
                annos = list(itertools.chain.from_iterable(self._annos))

                # Create annotations.
                StringAnnotation.objects.bulk_create(annos)

                # Create annotation edits.
                edits = [
                    StringAnnotationEdit(
                        action=StringAnnotationEdit.ACTION_SET,
                        clip=a.clip,
                        info=a.info,
                        value=a.value,
                        creation_time=a.creation_time,
                        creating_job=a.creating_job,
                        creating_processor=a.creating_processor)
                    for a in annos]
                StringAnnotationEdit.objects.bulk_create(edits)

            if len(self._tags) != 0:
                # there are tags to create

                # Get list of tags to create.
                tags = list(itertools.chain.from_iterable(self._tags))

                # Create tags.
                Tag.objects.bulk_create(tags)

                # Create tag edits.
                edits = [
                    TagEdit(
                        action=TagEdit.ACTION_SET,
                        clip=t.clip,
                        info=t.info,
                        creation_time=t.creation_time,
                        creating_job=t.creating_job,
                        creating_processor=t.creating_processor)
                    for t in tags]
                TagEdit.objects.bulk_create(edits)

            # Clear clips and annotations for next batch.
            self._clips.clear()
            self._annos.clear()
            self._tags.clear()
