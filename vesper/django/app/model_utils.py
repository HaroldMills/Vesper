"""Utility functions pertaining to models."""


from collections import defaultdict
from pathlib import Path
import datetime
import itertools

from django.db import transaction
from django.db.models import Count, F

from vesper.django.app.models import (
    AnnotationInfo, Clip, DeviceConnection, Recording, RecordingChannel,
    StationDevice, StringAnnotation, StringAnnotationEdit, Tag, TagEdit,
    TagInfo)
from vesper.singleton.archive import archive
from vesper.singleton.recording_manager import recording_manager
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils
import vesper.util.archive_lock as archive_lock


# TODO: Rename this module to `archive_utils`?

# TODO: Decide on criteria for what belongs in this module and what
# belongs in the `archive` singleton. One consideration is that the
# singleton has state (e.g. caches), while this module does not.


def get_station_mic_output_pairs_dict():
    
    """
    Gets a mapping from (station, microphone output) pair UI names to the
    pairs.
    """
    
    pairs = _get_station_mic_output_pairs()
    get_ui_name = get_station_mic_output_pair_ui_name
    return dict((get_ui_name(p), p) for p in pairs)


def get_station_mic_output_pairs_list():
    
    """
    Gets a list of all (station, microphone output) pairs.
    
    The pairs are sorted by their UI names.
    """
    
    pairs = _get_station_mic_output_pairs()
    get_ui_name = get_station_mic_output_pair_ui_name
    return sorted(pairs, key=get_ui_name)


def _get_station_mic_output_pairs():
    
    """Gets an unsorted list of all (station, microphone output) pairs."""
    
    station_mics = StationDevice.objects.filter(
        device__model__type='Microphone')
    
    return list(
        itertools.chain.from_iterable(
            _get_station_mic_output_pairs_aux(sm) for sm in station_mics))
    
    
def _get_station_mic_output_pairs_aux(sm):
    
    """
    Gets a list of all (station, microphone output) pairs for one
    station and microphone.
    """
    
    return [(sm.station, output) for output in sm.device.outputs.all()]


def get_station_mic_output_pair_ui_name(pair):
    
    """Gets the UI name of one (station, microphone output) pair."""
    
    station, mic_output = pair
    mic_output_name = mic_output.name
    if mic_output_name.endswith(' Output'):
        mic_output_name = mic_output_name[:-len(' Output')]
    return station.name + ' / ' + mic_output_name


def get_station_mic_output_pair_ui_names():
    
    """
    Gets a sorted list of all (station, microphone output) pair UI names.
    """
    
    pairs = _get_station_mic_output_pairs()
    return sorted(get_station_mic_output_pair_ui_name(p) for p in pairs)
    
    
def get_recording_channel_num_pairs(
        station, microphone_output, time_interval=None):
    
    """
    Gets (recording, channel number) pairs for the specified station,
    microphone output, and time interval. Each pair represents a
    channel of a recording made at the specified station from the
    specified microphone output whose interval intersects the specified
    time interval.
    
    The time interval may be `None`, in which case all recordings made at
    the station are returned. The start and/or end times of the time
    interval may also be `None`, denoting times of minus and plus
    infinity, respectively.
    
    The returned pairs are ordered by recording start time and channel
    number.
    """
    
    # Get recordings for the specified station whose time intervals
    # intersect the specified time interval.
    recordings = get_station_recordings(station, time_interval)
         
    rm_infos = get_recorder_microphone_infos(station, microphone_output)

    # Limit the recordings to those that involved the specified
    # microphone output.
    microphone_output_id = microphone_output.id
    pairs = []
    for r in recordings:
        channel_num = get_microphone_output_channel_num(
            r, microphone_output_id, rm_infos)
        if channel_num is not None:
            pairs.append((r, channel_num))
            
    return pairs
        

def get_station_recordings(station, time_interval=None):
    
    """
    Gets the recordings made at the specified station whose time intervals
    intersect the specified time interval.
    
    The time interval may be `None`, in which case all recordings made at
    the station are returned. The start and/or end times of the time
    interval may also be `None`, denoting times of minus and plus
    infinity, respectively.
    
    The returned recordings are ordered by start time.
    """
    
    
    if time_interval is None:
        # no time interval specified
        
        recordings = Recording.objects.filter(station=station)
    
    else:
        
        start, end = time_interval
        
        if start is None and end is None:
            # neither start nor end time specified
            
            recordings = Recording.objects.filter(station=station)
        
        elif end is None:
            # start time specified, but not end time
            
            recordings = Recording.objects.filter(
                station=station).exclude(
                end_time__lte=start)
                
        elif start is None:
            # end time specified, but not start time
            
            recordings = Recording.objects.filter(
                station=station).exclude(
                start_time__gte=end)
                
        else:
            # both start and end times specified
            
            recordings = Recording.objects.filter(
                station=station).exclude(
                end_time__lte=start).exclude(
                start_time__gte=end)
                
    return recordings.order_by('start_time')

            
def get_recorder_microphone_infos(station, microphone_output):
    
    """
    Gets a mapping from (recorder_id, microphone_output_id) pairs
    to lists of (channel_num, start_time, end_time) bunches.
    
    The bunches are ordered by channel numbers and start times.
    """
    
    # Get recorders that were used at station.
    recorders = station.devices.filter(model__type='Audio Recorder')
    
    rm_infos = defaultdict(list)
    
    for recorder in recorders:
        
        key = (recorder.id, microphone_output.id)
        
        # Get connections from microphone to recorder.
        connections = DeviceConnection.objects.filter(
            output=microphone_output,
            input__device=recorder)
        
        # Remember channel number and time interval of each connection.
        for connection in connections:
            info = Bunch(
                channel_num=connection.input.channel_num,
                start_time=connection.start_time,
                end_time=connection.end_time)
            rm_infos[key].append(info)
            
        rm_infos[key].sort(key=_get_rm_info_sort_key)

    return rm_infos
        
        
def _get_rm_info_sort_key(i):
    return (i.channel_num, i.start_time)


def get_microphone_output_channel_num(
        recording, microphone_output_id, recorder_microphone_infos):
    
    """
    Gets the channel number of the specified microphone output in the
    specified recording, or `None` if the microphone output was not
    involved in the recording.
    
    `recorder_microphone_infos` is a mapping from
    `(recorder_id, microphone_output_id)` pairs to lists of
    `(channel_num, start_time, end_time)` bunches.
    """
    
    # TODO: What should we do a situation in which a single microphone
    # output is connected to more than one recorder input, for example
    # with different input gains? In the following, we simply return
    # the channel number of the first input we encounter. Any other
    # inputs are ignored.
    
    recorder = recording.recorder
    infos = recorder_microphone_infos[(recorder.id, microphone_output_id)]
    start_time = recording.start_time
    
    for info in infos:
        
        if info.start_time <= start_time and start_time < info.end_time:
            # Microphone output was connected to recorder input
            # during recording. (We assume that equipment connections
            # do not change during recordings, so that if a microphone
            # output was connected to a recording's recorder at the
            # beginning of the recording it remained connected througout
            # the recording.)
            
            return info.channel_num
        
    # If we get here, the specified microphone output was not involved
    # in the specified recording.
    return None
        
    
def get_recordings(station, mic_output, time_interval):
    
    """
    Gets the recordings that involve the specified station and
    microphone output and that intersect the specified time
    interval.
    """
    
    start_time, end_time = time_interval
    
    channels = RecordingChannel.objects.filter(
        recording__station=station,
        mic_output=mic_output,
        recording__start_time__lt=end_time,
        recording__end_time__gt=start_time
    ).order_by(
        'recording__start_time'
    )
    
    return [c.recording for c in channels]


def get_recording_dates(station, mic_output):
    
    # This function currently assumes that a recording is contained
    # entirely in one night.
    # TODO: Make this work for recordings that span more than one night,
    # and for diurnal recordings.
    
    # TODO: Annotate channels with recording start times?
    channels = RecordingChannel.objects.filter(
        recording__station=station,
        mic_output=mic_output)
    
    nights = set(station.get_night(c.recording.start_time) for c in channels)
    
    return sorted(nights)


def get_absolute_recording_file_path(file_):
    
    if file_.path is None:
        return None
    
    else:
        
        path = Path(file_.path)
        
        if path.is_absolute():
            
            # For now, at least, we allow this for backward compatibility.
            # Maybe we should issue a deprecation warning, though, and
            # encourage path relativization?
            return path
        
        else:
            # path is relative
        
            return recording_manager.get_absolute_recording_file_path(path)


def get_clip_recording_file(clip):
    
    """
    Gets the recording file containing the specified clip.
    
    Parameters
    ----------
    clip : Clip
        the clip whose recording file is to be gotten.
        
    Returns
    -------
    RecordingFile or None
        the recording file containing the specified clip, or `None` if
        the recording has no files.
        
    Raises
    ------
    ValueError
        If the clip is not contained by a single recording file, for
        example if it straddles the boundary between two files.
    """
    
    recording = clip.recording_channel.recording
    files = recording.files
    num_files = files.count()
    
    if num_files == 0:
        return None
    
    else:
        
        for f in files.all().order_by('file_num'):
            
            file_end_index = f.end_index
            
            if clip.start_index < file_end_index:
                # clip starts in this file
                
                if clip.end_index <= file_end_index:
                    # clip is contained entirely in this file
                    
                    return f
                
                else:
                    # clip is not contained entirely in this file
                    
                    raise ValueError(
                        'Clip extends past end of recording file in which '
                        'it starts.')
            
        # We should never get here, since by definition a clip is part of
        # its parent recording.
        raise ValueError(
            'DATA INTEGRITY ERROR: Clip starts after end of last file of '
            'parent recording. This is not supposed to happen, and should '
            'be investigated ASAP.')


def get_clip_counts(
        station, mic_output, detector, annotation_name=None,
        annotation_value=None, tag_name=None):
    
    dates = get_recording_dates(station, mic_output)
    
    counts = dict((date, 0) for date in dates)
    
    clips = get_clips(
        station=station,
        mic_output=mic_output,
        detector=detector,
        annotation_name=annotation_name,
        annotation_value=annotation_value,
        tag_name=tag_name,
        order=False)
    
    count_dicts = clips.values('date').annotate(count=Count('date'))
    
    for d in count_dicts:
        counts[d['date']] = d['count']
    
#     print('_get_clip_counts', count_dicts.query)
#     
#     for date, count in counts.items():
#         print('_get_clip_counts {}: {}'.format(str(date), count))
    
    return counts
    
    
def get_clips(**kwargs):
    
    station = kwargs.get('station')
    mic_output = kwargs.get('mic_output')
    date = kwargs.get('date')
    detector = kwargs.get('detector')
    annotation_name = kwargs.get('annotation_name')
    annotation_value = kwargs.get('annotation_value')
    tag_name = kwargs.get('tag_name')
    order = kwargs.get('order', True)
    
    clips = _get_base_clips(station, mic_output, date, detector)
    
    clips = _filter_clips_by_annotation_if_needed(
        clips, annotation_name, annotation_value)
    
    clips = _filter_clips_by_tag_if_needed(clips, tag_name)
        
    if order:
        clips = clips.order_by('start_time')
        
    return clips


def _get_base_clips(station, mic_output, date, detector):
    
    kwargs = {}
    _add_kwarg_if_needed(kwargs, 'station', station)
    _add_kwarg_if_needed(kwargs, 'mic_output', mic_output)
    _add_kwarg_if_needed(kwargs, 'date', date)
    _add_kwarg_if_needed(kwargs, 'creating_processor', detector)
    
    if len(kwargs) == 0:
        return Clip.objects.all()
    else:
        return Clip.objects.filter(**kwargs)
    

def _add_kwarg_if_needed(kwargs, key, value):
    if value is not None:
        kwargs[key] = value
        

def _filter_clips_by_annotation_if_needed(
        clips, annotation_name, annotation_value):
    
    if annotation_name is None:
        # want all clips regardless of annotation
        
        return clips
    
    else:
        # want to filter clips according to annotation
        
        # TODO: What does SQL for clip queries look like?
        # Could we use `select_related` or `prefetch_related`
        # here to accelerate queries that involve annotations
        # and tags?
                
        info = AnnotationInfo.objects.get(name=annotation_name)
        
        if annotation_value is None:
            # want only unannotated clips
            
            return clips.exclude(string_annotation__info=info)
            
        else:
            # want only annotated clips
            
            wildcard = archive.STRING_ANNOTATION_VALUE_WILDCARD
            
            # Get all annotated clips.
            clips = clips.filter(string_annotation__info=info)
            
            if not annotation_value.endswith(wildcard):
                # want clips with a particular annotation value
                
                clips = clips.filter(string_annotation__value=annotation_value)
                
            elif annotation_value != wildcard:
                # want clips whose annotation values start with a prefix
                
                prefix = annotation_value[:-len(wildcard)]
                
                clips = clips.filter(
                    string_annotation__value__startswith=prefix)
                
            return clips
                

def _filter_clips_by_tag_if_needed(clips, tag_name):
    
    # TODO: Support tag exclusion as well as inclusion.

    if tag_name is None:
        return clips
    
    else:
        info = TagInfo.objects.get(name=tag_name)
        return clips.filter(tag__info=info)


def create_clip_query_values_iterator(
        sm_pair_ui_names, start_date, end_date, detector_names):
    
    # We create lists of station/mic output pairs, dates, and detectors
    # immediately so that if we will raise an exception due to a bad
    # station/mic output pair, date range, or detector name we do so
    # before we start yielding query values.
    
    sm_pairs_dict = get_station_mic_output_pairs_dict()
    sm_pairs = [sm_pairs_dict[name] for name in sm_pair_ui_names]
    
    dates = list(create_date_iterator(start_date, end_date))
    
    detectors = [archive.get_processor(name) for name in detector_names]

    for station, mic_output in sm_pairs:
        for date in dates:
            for detector in detectors:
                yield (station, mic_output, date, detector)
           
         
_ONE_DAY = datetime.timedelta(days=1)

  
def create_date_iterator(start_date, end_date):
    
    if end_date < start_date:
        return
    
    else:
        date = start_date
        while date <= end_date:
            yield date
            date += _ONE_DAY
    
    
def get_clip_annotations(clip):
    
    annotations = StringAnnotation.objects.filter(
        clip_id=clip.id
    ).annotate(name=F('info__name'))

    return dict((a.name, a.value) for a in annotations)


def get_clip_annotation_value(clip, annotation_info):

    try:
        annotation = StringAnnotation.objects.get(
            clip=clip, info=annotation_info)
        
    except StringAnnotation.DoesNotExist:
        return None
    
    else:
        return annotation.value


@archive_lock.atomic
@transaction.atomic
def annotate_clip(
        clip, annotation_info, value, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    try:
        annotation = StringAnnotation.objects.get(
            clip=clip,
            info=annotation_info)
        
    except StringAnnotation.DoesNotExist:
        annotation = None
    
    if annotation is None or annotation.value != value:
        # annotation does not exist or value differs from specified value
        
        if creation_time is None:
            creation_time = time_utils.get_utc_now()
        
        kwargs = {
            'value': value,
            'creation_time': creation_time,
            'creating_user': creating_user,
            'creating_job': creating_job,
            'creating_processor': creating_processor
        }
    
        if annotation is None:
            # clip is not annotated
            
            StringAnnotation.objects.create(
                clip=clip,
                info=annotation_info,
                **kwargs)
            
        else:
            # clip is annotated but value differs from specified value
            
            StringAnnotation.objects.filter(
                clip=clip,
                info=annotation_info
            ).update(**kwargs)
            
        StringAnnotationEdit.objects.create(
            clip=clip,
            info=annotation_info,
            action=StringAnnotationEdit.ACTION_SET,
            **kwargs)
    
    
@archive_lock.atomic
@transaction.atomic
def unannotate_clip(
        clip, annotation_info, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    try:
        annotation = StringAnnotation.objects.get(
            clip=clip,
            info=annotation_info)
        
    except StringAnnotation.DoesNotExist:
        # clip is not annotated
        
        return
    
    else:
        # clip is annotated
    
        annotation.delete()
    
        if creation_time is None:
            creation_time = time_utils.get_utc_now()
         
        StringAnnotationEdit.objects.create(
            clip=clip,
            info=annotation_info,
            action=StringAnnotationEdit.ACTION_DELETE,
            creation_time=creation_time,
            creating_user=creating_user,
            creating_job=creating_job,
            creating_processor=creating_processor)


@archive_lock.atomic
@transaction.atomic
def tag_clip(
        clip, tag_info, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    try:
        _ = Tag.objects.get(
            clip=clip,
            info=tag_info)
        
    except Tag.DoesNotExist:
        # clip is not already tagged
         
        if creation_time is None:
            creation_time = time_utils.get_utc_now()
        
        kwargs = {
            'creation_time': creation_time,
            'creating_user': creating_user,
            'creating_job': creating_job,
            'creating_processor': creating_processor
        }
    
        Tag.objects.create(
            clip=clip,
            info=tag_info,
            **kwargs)
            
        TagEdit.objects.create(
            clip=clip,
            info=tag_info,
            action=TagEdit.ACTION_SET,
            **kwargs)
    
    
@archive_lock.atomic
@transaction.atomic
def untag_clip(
        clip, tag_info, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    try:
        tag = Tag.objects.get(
            clip=clip,
            info=tag_info)
        
    except Tag.DoesNotExist:
        # clip is not tagged
        
        return
    
    else:
        # clip is tagged
    
        tag.delete()
    
        if creation_time is None:
            creation_time = time_utils.get_utc_now()
         
        TagEdit.objects.create(
            clip=clip,
            info=tag_info,
            action=TagEdit.ACTION_DELETE,
            creation_time=creation_time,
            creating_user=creating_user,
            creating_job=creating_job,
            creating_processor=creating_processor)
    
    
def get_clip_detector_name(clip):
    
    processor = clip.creating_processor
    
    if processor is None:
        return None
    
    else:
        return processor.name


def get_clip_type(clip):
    
    processor = clip.creating_processor
    
    if processor is None:
        return None
    
    elif 'Tseep' in processor.name:
        return 'Tseep'
    
    elif 'Thrush' in processor.name:
        return 'Thrush'
    
    else:
        return None


def get_clip_query_annotation_data(annotation_name, annotation_value):
    
    value = archive.get_string_annotation_archive_value(
        annotation_name, annotation_value)
    
    if value == archive.NOT_APPLICABLE:
        return None, None
    
    elif value == archive.STRING_ANNOTATION_VALUE_NONE:
        return annotation_name, None
    
    else:
        return annotation_name, value


def get_clip_query_tag_name(tag_name):
    if tag_name == archive.NOT_APPLICABLE:
        return None
    else:
        return tag_name
