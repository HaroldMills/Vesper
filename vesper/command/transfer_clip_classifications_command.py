"""Module containing class `TransferClipClassificationsCommand`."""


import logging

from vesper.command.command import Command
from vesper.django.app.models import AnnotationInfo, Job, Processor
from vesper.singleton.archive import archive
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.matching_utils as matching_utils
import vesper.util.time_utils as time_utils


_DURATION_THRESHOLD = .7
"""
Matching clip intersection duration threshold, a fraction of the minimum
clip duration of a clip pair.
"""


_logger = logging.getLogger()


class TransferClipClassificationsCommand(Command):
    
    """
    Command that transfers classifications from clips of one detector
    to clips of another.
    
    Arguments:
    * source detector
    * target detector
    * station/mic output pairs
    * start date
    * end date
    * classification
    
    For each recording of specified station/mics and dates, the command
    matches classified source clips with unclassified target clips, and
    classifies the target clips accordingly.
    
    The matching algorithm pairs an unclassified target clip with the
    first classified source clip that intersects it maximally, provided
    the duration of the intersection is at least some fraction of the
    minimum of the clip durations.
    """


    extension_name = 'transfer_clip_classifications'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._source_detector_name = get('source_detector', args)
        self._target_detector_name = get('target_detector', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._annotation_value = get('classification', args)
        
        
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)

        self._source_detector = _get_detector(self._source_detector_name)
        self._target_detector = _get_detector(self._target_detector_name)
        
        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', self._annotation_value)
            
        self._annotation_info = _get_annotation_info(self._annotation_name)

        self._transfer_classifications()
        
        return True
    
    
    def _create_clip_query_values_iterator(self):
        
        try:
            return model_utils.create_clip_query_values_iterator(
                self._sm_pair_ui_names, self._start_date, self._end_date,
                [self._source_detector_name])
            
        except Exception as e:
            command_utils.log_and_reraise_fatal_exception(
                e, 'Clip query values iterator construction',
                'The archive was not modified.')


    def _transfer_classifications(self):
        value_tuples = self._create_clip_query_values_iterator()
        for station, mic_output, date, _ in value_tuples:
            self._transfer_classifications_aux(station, mic_output, date)
    
    
    def _transfer_classifications_aux(self, station, mic_output, date):
    
        # Get source clips with specified annotation.
        source_clips = model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=self._source_detector,
            annotation_name=self._annotation_name,
            annotation_value=self._annotation_value)
    
        # Get unannotated target clips.
        target_clips = model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=self._target_detector,
            annotation_name=self._annotation_name,
            annotation_value=None)
    
        matches = _match_clips(source_clips, target_clips, date)
    
        _logger.info(
            f'{self._source_detector.name} -> {self._target_detector.name} / '
            f'{station.name} / {mic_output.name} / {date} / '
            f'{source_clips.count()}  {target_clips.count()} {len(matches)}')
    
        if len(matches) > 0:
    
            source_clips = list(source_clips.all())
            target_clips = list(target_clips.all())
    
            # self._show_matches(matches, source_clips, target_clips)
    
            for i, j in matches:
                self._transfer_classification(source_clips[i], target_clips[j])
    
    
    def _show_clips(
            self, source_clips, source_centers, target_clips, target_centers):
    
        source_start_times = [c.start_time for c in source_clips.all()]
        target_start_times = [c.start_time for c in target_clips.all()]
    
        source_data = [
            ('source', i, str(start_time), center)
            for i, (start_time, center)
            in enumerate(zip(source_start_times, source_centers))]
    
        target_data = [
            ('target', i, str(start_time), center)
            for i, (start_time, center)
            in enumerate(zip(target_start_times, target_centers))]
    
        data = source_data + target_data
        data.sort(key=lambda d: d[2])
    
        for d in data:
            print(d)
    
    
    def _show_matches(self, matches, source_clips, target_clips):
    
        min_diff = 1e6
        max_diff = -1e6
    
        for k, (i, j) in enumerate(matches):
    
            s = source_clips[i]
            t = target_clips[j]
    
            fs = s.sample_rate
    
            diff = (t.start_index - s.start_index) / fs
    
            print(
                f'{k} {s.start_index / fs:.3f} {t.end_index / fs:.3f} '
                f'{diff:.3f}')
    
            min_diff = min(diff, min_diff)
            max_diff = max(diff, max_diff)
    
        print('diff range [{min_diff:.3f}, {max_diff:.3f}]')
    
    
    def _transfer_classification(self, source_clip, target_clip):
    
        # Get source clip classification.
        annotations = model_utils.get_clip_annotations(source_clip)
        classification = annotations.get(self._annotation_name)
        
        # Classify target clip. 
        model_utils.annotate_clip(
            target_clip, self._annotation_info, classification,
            creating_job=self._job)
            
            
def _get_detector(name):
    try:
        return archive.get_processor(name)
    except Processor.DoesNotExist as e:
        command_utils.log_and_reraise_fatal_exception(
            e, 'Detector lookup', 'The archive was not modified.')


def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(type='String', name=name)
    except AnnotationInfo.DoesNotExist as e:
        command_utils.log_and_reraise_fatal_exception(
            e, 'Annotation info lookup', 'The archive was not modified.')
        
        
def _match_clips(source_clips, target_clips, date):
    
    if source_clips.count() == 0 or target_clips.count() == 0:
        # have no source clips or no target clips

        # In this simple case we know there are no matches, so
        # we go ahead and return an empty list. We would get the
        # same result if we executed the code in the `else` clause
        # below, but that might waste considerable time, for example
        # if there are no source clips but many target clips.
        return []

    else:
        # have both source clips and target clips
        
        reference_time = time_utils.create_utc_datetime(
            date.year, date.month, date.day)
        
        source_intervals = _get_intervals(source_clips, reference_time)
        target_intervals = _get_intervals(target_clips, reference_time)
        
        return matching_utils.match_intervals(
            source_intervals, target_intervals, _DURATION_THRESHOLD)
        
    
def _get_intervals(clips, reference_time):
    return [_get_interval(c, reference_time) for c in clips.all()]


def _get_interval(clip, reference_time):
    start = _get_offset(clip.start_time, reference_time)
    end = _get_offset(clip.end_time, reference_time)
    return (start, end)


def _get_offset(time, reference_time):
    return (time - reference_time).total_seconds()
