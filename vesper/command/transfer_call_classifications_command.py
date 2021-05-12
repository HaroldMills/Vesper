"""Module containing class `TransferCallClassificationsCommand`."""


import logging

from vesper.command.command import Command
from vesper.django.app.models import AnnotationInfo, Job, Processor
from vesper.singleton.archive import archive
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.time_utils as time_utils


'''
Transfer call classifications from clips of one detector to clips of another.

Arguments:
* source detector
* target detector
* station/mic output pairs
* start date
* end date

The command will support only detectors for which call start times are
within a known window.

For each recording of the specified station/mics and dates, the command will
match call clips of the source detector with unclassified clips of the target
detector, and classify the target detector clips accordingly.

The matching algorithm will match a source detector call clip with a target
detector clip if their call start windows intersect. A source detector call
clip's call start window intersects the call start window of a target
detector clip if and only if the center of the call clip's window is within
a window with the same center as the target detector clip's call start window,
and whose width is the maximum of the call start window widths of the two
detectors. Thus we can use the same matching code we use to evaluate
detectors on the BirdVox-full-night recordings to perform the transfer
matching.
'''


_CALL_START_WINDOWS = {
    
    # Thrush call detectors.
    'Old Bird Thrush Detector': (.130, .220),
    'PNF 2018 Baseline Thrush Detector 1.0': (.100, .150),
    'PNF Thrush Energy Detector 1.0': (.050, .125),
    'MPG Ranch Thrush Detector': (.080, .440),
    
    # Tseep call detectors.
    'Old Bird Tseep Detector': (.100, .135),
    'PNF 2018 Baseline Tseep Detector 1.0': (.070, .105),
    'PNF Tseep Energy Detector 1.0': (.050, .115),
    'MPG Ranch Tseep Detector': (.070, .280),
    
    # Other detectors.
    'BirdVoxDetect': (.280, .420),
    
}
"""
Windows within clips where call starts occur.

For a particular detector, a detected call will start within a certain
limited window within the call's clip. This attribute maps detector
names to call start window bounds. The units of the bounds are seconds
after the clip start.
"""


_logger = logging.getLogger()


class TransferCallClassificationsCommand(Command):
    
    
    extension_name = 'transfer_call_classifications'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._source_detector_name = get('source_detector', args)
        self._target_detector_name = get('target_detector', args)
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
    def execute(self, job_info):
        
        self._job = Job.objects.get(id=job_info.job_id)

        self._source_detector = _get_detector(self._source_detector_name)
        self._target_detector = _get_detector(self._target_detector_name)
        
        self._source_call_start_window = \
            _get_call_start_window(self._source_detector_name)
        self._target_call_start_window = \
            _get_call_start_window(self._target_detector_name)
        
        self._annotation_name, self._annotation_value = \
            model_utils.get_clip_query_annotation_data(
                'Classification', 'Call*')
            
        self._annotation_info = _get_annotation_info(self._annotation_name)

        # When we match clips, we use times in seconds after a reference
        # time, specifically midnight of the date specified for the
        # start date parameter of this command.
        self._reference_time = self._get_reference_time()
        
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


    def _get_reference_time(self):
        d = self._start_date
        return time_utils.create_utc_datetime(d.year, d.month, d.day)
    
    
    def _transfer_classifications(self):
        value_tuples = self._create_clip_query_values_iterator()
        for station, mic_output, date, _ in value_tuples:
            self._transfer_classifications_aux(station, mic_output, date)
            
            
    def _transfer_classifications_aux(self, station, mic_output, date):
        
        source_clips = model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=self._source_detector,
            annotation_name=self._annotation_name,
            annotation_value=self._annotation_value)
                
        target_clips = model_utils.get_clips(
            station=station,
            mic_output=mic_output,
            date=date,
            detector=self._target_detector,
            annotation_name=self._annotation_name)
        
        matches = self._match_clips_with_calls(source_clips, target_clips)
        
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
            

    def _match_clips_with_calls(self, source_clips, target_clips):
        
        if source_clips.count() == 0 or target_clips.count() == 0:
            # have no source clips or no target clips
            
            # In this simple case we know there are no matches, so
            # we go ahead and return an empty list. We would get the
            # same result if we executed the code in the `else` clause
            # below, but that might waste considerable time (for example,
            # if there are no source clips but many target clips).
            return []
        
        else:
            # have both source clips and target clips
            
            source_centers = _get_call_start_window_centers(
                source_clips, self._reference_time,
                self._source_call_start_window)
            
            target_centers = _get_call_start_window_centers(
                target_clips, self._reference_time,
                self._target_call_start_window)
            
            # self._show_clips(
            #     source_clips, source_centers, target_clips, target_centers)
            
            max_distance = _get_matching_max_distance(
                self._source_call_start_window, self._target_call_start_window)
            
            return _match_events(source_centers, target_centers, max_distance)
        

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
            
            print('{} {:.3f} {:.3f} {:.3f}'.format(
                k, s.start_index / fs, t.start_index / fs, diff))
            
            min_diff = min(diff, min_diff)
            max_diff = max(diff, max_diff)
            
        print('diff range [{:.3f}, {:.3f}]'.format(min_diff, max_diff))
        
        
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


def _get_call_start_window(detector_name):
    
    result = _CALL_START_WINDOWS.get(detector_name)
    
    if result is None:
        # no `_CALL_START_WINDOWS` key is exactly `detector_name`
        
        # Look for key that is a prefix of `detector_name`.
        for name, window in _CALL_START_WINDOWS.items():
            if detector_name.startswith(name):
                result = window
                
        if result is None:
            # no `_CALL_START_WINDOWS` key is a prefix of `detector_name`
            
            raise ValueError(
                f'Could not find call start window for detector '
                f'"{detector_name}". The archive was not modified.')
        
    return result
        

def _get_call_start_window_centers(clips, reference_time, window):
    
    # Get offset from start of clip to center of call start window.
    start, end = window
    offset = (start + end) / 2
    
    return [
        (c.start_time - reference_time).total_seconds() + offset
        for c in clips.all()]


def _get_annotation_info(name):
    try:
        return AnnotationInfo.objects.get(type='String', name=name)
    except AnnotationInfo.DoesNotExist as e:
        command_utils.log_and_reraise_fatal_exception(
            e, 'Annotation info lookup', 'The archive was not modified.')
        
        
def _get_matching_max_distance(source_window, target_window):
    
    # Get source call start window duration.
    start, end = source_window
    source_duration = end - start
    
    # Get target call start window duration.
    start, end = target_window
    target_duration = end - start
    
    return (source_duration + target_duration) / 2


# TODO: Characterize this algorithm. Does it find a maximal matching?
# (I suspect so, since it matches a reference event to the *first*
# available estimate event whose window contains it, which keeps as
# many options open as possible for matching later reference events.)
# If so, can the matching differ from that found by the mir_eval
# algorithm, and does that matter? When there is more than one maximal
# matching, this algorithm may not find the one that is optimal in the
# sense that the sum of the distances between the paired references and
# estimates is minimal. Is that of any practical importance? Could this
# algorithm be modified to yield the optimal matching?
def _match_events(references, estimates, max_distance):
    
    num_references = len(references)
    num_estimates = len(estimates)
    
    i = 0
    j = 0
    
    matches = []
    
    while i != num_references and j != num_estimates:
        
        diff = references[i] - estimates[j]
        
        if diff < -max_distance:
            # reference i precedes estimate j by more than max distance
            
            i += 1
            
        elif diff > max_distance:
            # reference i follows reference j by more than max distance
            
            j += 1
            
        else:
            # reference i is within max distance of estimate j
                        
            matches.append((i, j))
            
            i += 1
            j += 1
            
    return matches
