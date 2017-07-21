"""Utility functions pertaining to models."""


from collections import defaultdict
import datetime
import itertools

from django.db.models import Count

from vesper.django.app.models import (
    AnnotationInfo, Clip, DeviceConnection, Processor, Recording,
    RecordingChannel, StationDevice, StringAnnotation, StringAnnotationEdit)
from vesper.singletons import preference_manager
from vesper.util.bunch import Bunch
import vesper.util.time_utils as time_utils


WILDCARD = '*'
_ONE_DAY = datetime.timedelta(days=1)


def get_station_mic_output_pairs_dict():
    
    """
    Gets a mapping from (station, microphone output) pair UI names to the pairs.
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
    """
    
    
    if time_interval is None:
        # no time interval specified
        
        return Recording.objects.filter(station=station)
    
    else:
        
        start, end = time_interval
        
        if start is None and end is None:
            # neither start nor end time specified
            
            return Recording.objects.filter(station=station)
        
        elif end is None:
            # start time specified, but not end time
            
            return Recording.objects.filter(
                station=station).exclude(
                end_time__lte=start)
                
        elif start is None:
            # end time specified, but not start time
            
            return Recording.objects.filter(
                station=station).exclude(
                start_time__gte=end)
                
        else:
            # both start and end times specified
            
            return Recording.objects.filter(
                station=station).exclude(
                end_time__lte=start).exclude(
                start_time__gte=end)

            
def get_recorder_microphone_infos(station, microphone_output):
    
    """
    Gets a mapping from (recorder_id, microphone_output_id) pairs
    to lists of (channel_num, start_time, end_time) bunches.
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
            
    return rm_infos
        
        
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
    
    return nights


def get_clip_counts(
        station, mic_output, detector, annotation_name=None,
        annotation_value=None):
    
    dates = get_recording_dates(station, mic_output)
    
    counts = dict((date, 0) for date in dates)
    
    clips = get_clips(
        station, mic_output, detector, annotation_name=annotation_name,
        annotation_value=annotation_value)
    
    count_dicts = clips.values('date').annotate(count=Count('date'))
    
    for d in count_dicts:
        counts[d['date']] = d['count']
    
#     print('_get_clip_counts', count_dicts.query)
#     
#     for date, count in counts.items():
#         print('_get_clip_counts {}: {}'.format(str(date), count))
    
    return counts
    
    
def get_clips(
        station, mic_output, detector, date=None, annotation_name=None,
        annotation_value=None):
    
    kwargs = {}
    if date is not None:
        kwargs['date'] = date
        
    # Get all clips, whether or not they are annotated.
    clips = Clip.objects.filter(
        station=station,
        mic_output=mic_output,
        creating_processor=detector,
        **kwargs)
    
    if annotation_name is not None:
        # whether or not clips are annotated will matter
        
        info = AnnotationInfo.objects.get(name=annotation_name)
        
        if annotation_value is None:
            # want only unannotated clips
            
            clips = clips.exclude(string_annotation__info=info)
            
        else:
            # want only annotated clips
            
            # Get all annotated clips.
            clips = clips.filter(string_annotation__info=info)
            
            if not annotation_value.endswith(WILDCARD):
                # want clips with a particular annotation value
                
                clips = clips.filter(string_annotation__value=annotation_value)
                
            elif annotation_value != WILDCARD:
                # want clips whose annotation values start with a prefix
                
                prefix = annotation_value[:-len(WILDCARD)]
                
                clips = clips.filter(
                    string_annotation__value__startswith=prefix)
                
    return clips


def get_processors(type, include_hidden=False):
    
    processors = Processor.objects.filter(type=type).order_by('name')
    
    if include_hidden:
        return processors
    
    else:
        hidden = _get_hidden_processors()
        return [p for p in processors if (p.name, type) not in hidden]


def _get_hidden_processors():
    preferences = preference_manager.instance.preferences
    processors = preferences.get('hidden_processors', [])
    processors = [_get_processor_pair(p) for p in processors]
    return frozenset(p for p in processors if p is not None)


def _get_processor_pair(p):
    try:
        return (p['name'], p['type'])
    except Exception:
        return None
    

def get_processor(name, type):
    return Processor.objects.get(name=name, type=type)


def create_clip_iterator(
        detector_names, sm_pair_ui_names, start_date, end_date):

    """Generator that returns a clip iterator."""
    
    detectors = [_get_detector(name) for name in detector_names]

    sm_pairs_dict = get_station_mic_output_pairs_dict()
    sm_pairs = [sm_pairs_dict[name] for name in sm_pair_ui_names]
    
    date_range = (start_date, end_date)
    
    for detector in detectors:
        
        for station, mic_output in sm_pairs:
            
            clips = Clip.objects.filter(
                station=station,
                mic_output=mic_output,
                date__range=date_range,
                creating_processor=detector)
                
            for clip in clips:
                yield clip


def _get_detector(name):
    try:
        return get_processor(name, 'Detector')
    except Processor.DoesNotExist:
        raise ValueError(
            'Unrecognized detector "{}".'.format(name))


def annotate_clip(
        clip, annotation_info, value, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    # We assume that any database locking and/or transaction management
    # involved in deleting a clip happens in the caller.
    
    if creation_time is None:
        creation_time = time_utils.get_utc_now()
    
    defaults = {
        'value': value,
        'creation_time': creation_time,
        'creating_user': creating_user,
        'creating_job': creating_job,
        'creating_processor': creating_processor
    }
    
    StringAnnotation.objects.update_or_create(
        clip=clip,
        info=annotation_info,
        defaults=defaults)

    StringAnnotationEdit.objects.create(
        clip=clip,
        info=annotation_info,
        action=StringAnnotationEdit.ACTION_SET,
        **defaults)
    
    
def delete_clip_annotation(
        clip, annotation_info, creation_time=None, creating_user=None,
        creating_job=None, creating_processor=None):
    
    # We assume that any database locking and/or transaction management
    # involved in deleting a clip happens in the caller.
    
    try:
        annotation = StringAnnotation.objects.get(
            clip=clip,
            info=annotation_info)
        
    except StringAnnotation.DoesNotExist:
        return
    
    else:
    
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
