from zoneinfo import ZoneInfo
import datetime
import time
import unittest

from django.db.models import Q
from django.test import TestCase

from vesper.django.app.models import (
    AnnotationInfo, Clip, Device, DeviceModel, Recording, Station,
    StationDevice, StringAnnotation)
import vesper.django.app.model_utils as model_utils
import vesper.util.yaml_utils as yaml_utils


def _dt(*args):
    return datetime.datetime(*args, tzinfo=ZoneInfo('UTC'))


_DATABASE_YAML = '''
    clips:
        - annotations: {A: Call, B: Call}
        - annotations: {A: Call, B: Noise}
        - annotations: {A: Call}
        - annotations: {B: Call}
        - annotations: {B: Tone}
'''


class ClipTestCase(TestCase):
    
    
    def tearDown(self):
        _depopulate_database()
        
        
    @unittest.skip('')
    def test_conjunctive_annotation_query_of_clip_table(self):
        
        # This query yields clips whose annotations
        _populate_database_from_yaml(_DATABASE_YAML)
        
        a = AnnotationInfo.objects.get(name='A')
        b = AnnotationInfo.objects.get(name='B')
        
        clips = Clip.objects.filter(
            string_annotation__info=a,
            string_annotation__value='Call'
        ).filter(
            string_annotation__info=b,
            string_annotation__value='Call')
        
        _show_clips(clips)
        
        
    def test_disjunctive_annotation_query_of_annotation_table(self):
        
        # This query yields annotation objects that satisfy a disjunction
        # of terms. Positive conjunctive terms can be added by specifying
        # more arguments to the `filter` function, or by chaining
        # additional calls to the `filter` function. Negative conjunctive
        # terms can be specified as arguments to the `exclude` function.
        # 
        # An annotation's clip object can be fetched as part of the query
        # using `select_related`.
        #
        # Note that this sort of query can return more than one annotation
        # for the same clip, for example if one requests annotations having
        # different names.
        
        _populate_database_from_yaml(_DATABASE_YAML)
        
        b = AnnotationInfo.objects.get(name='B')
        call = Q(info=b, value='Call')
        noise = Q(info=b, value='Noise')
        
        annotations = StringAnnotation.objects.filter(call | noise)
        _show_annotations(annotations)
        

    def test_disjunctive_annotation_query_of_clip_table(self):
        
        # This query yields clips whose annotations satisfy the disjunction
        # of one or more conditions. Different clauses of the disjunction
        # can refer to different annotations if needed.
        #
        # One can specify more than one argument to the `filter` method
        # to conjoin positive terms, and call the `exclude` method to
        # conjoin negative terms. One can also negate a disjunctive term
        # with the `~` operator.
        #
        # As far as I know, one must execute an additional query on
        # a clip from the resulting query set to get its annotation
        # values. No annotation values arrive with the clip from the
        # first query, even if that query used some of them. Perhaps
        # there's some way to include these values with the clips that
        # I haven't figured out yet.
        
        _populate_database_from_yaml(_DATABASE_YAML)
        
        b = AnnotationInfo.objects.get(name='B')
        
        call = Q(
            string_annotation__info=b,
            string_annotation__value='Call')
         
        noise = Q(
            string_annotation__info=b,
            string_annotation__value='Noise')
         
        clips = Clip.objects.filter(call | noise)
         
        _show_clips(clips)
        

    @unittest.skip('')
    def test_unclassified_clips_query(self):
        _populate_database(10)
        classification = AnnotationInfo.objects.get(name='Classification')
        clips = Clip.objects.exclude(string_annotation__info=classification)
        _show_clips(clips)
                    
            
    @unittest.skip('')
    def test_unclassified_clips_query_performance(self):
        _populate_database(100000, self._time_unclassified_clip_query, 10000)
        
        
    def _time_unclassified_clip_query(self, i):
        
        classification = AnnotationInfo.objects.get(name='Classification')
          
        start = time.time()
        clips = Clip.objects.exclude(
            string_annotation__info=classification)
        end_query = time.time()
        length = 0
        for clip in clips:
            length += clip.length
        end_enum = time.time()
        query_time = end_query - start
        enum_time = end_enum - end_query
        items = (i, len(clips), length, query_time, enum_time)
        print(','.join(str(item) for item in items))


def _show_clips(clips):
    print(clips.query)
    for clip in clips:
        print(clip)
        for annotation in clip.string_annotations.all():
            print(annotation.info.name, annotation.value)


def _show_annotations(annotations):
    print(annotations.query)
    for annotation in annotations:
        print(annotation)
        print(annotation.clip)
        
        
_RECORDING_START_TIME = _dt(2017, 3, 1)
_NUM_CHANNELS = 1
_SAMPLE_RATE = 22050.
_CLIP_DURATION = 1


def _populate_database_from_yaml(s):
    
    d = yaml_utils.load(s)
    
    num_stations = d.get('num_stations', 1)
    stations = []
    for i in range(num_stations):
        name = 'Station {}'.format(i + 1)
        station = Station.objects.create(name=name, time_zone='US/Eastern')
        stations.append(station)
        
    model = DeviceModel.objects.create(
        name='Recorder Model', type='Recorder', manufacturer='Nagra',
        model='X')
    
    device = Device.objects.create(
        name='Recorder', model=model, serial_number='0')
    
    clips = d['clips']
    num_clips = len(clips)
    clip_length = _CLIP_DURATION * _SAMPLE_RATE
    recording_length = num_clips * clip_length
    recording_duration = recording_length / _SAMPLE_RATE
    recording_end_time = \
        _RECORDING_START_TIME + datetime.timedelta(seconds=recording_duration)
    
    station_recorder = StationDevice.objects.create(
        station=station, device=device, start_time=_RECORDING_START_TIME,
        end_time=recording_end_time)
    
    creation_time = _RECORDING_START_TIME
    
    recording = Recording.objects.create(
        station_recorder=station_recorder, num_channels=_NUM_CHANNELS,
        length=recording_length, sample_rate=_SAMPLE_RATE,
        start_time=_RECORDING_START_TIME, end_time=recording_end_time,
        creation_time=creation_time)
    
    annotation_names = _get_annotation_names(clips)
    annotation_infos = dict(
        (name, _create_annotation_info(name, creation_time))
        for name in annotation_names)
    
    for i, clip_d in enumerate(clips):
        
        clip_start_index = i * clip_length
        offset = clip_start_index / _SAMPLE_RATE
        clip_start_time = \
            _RECORDING_START_TIME + datetime.timedelta(seconds=offset)
        clip_duration = clip_length / _SAMPLE_RATE
        clip_end_time = \
            clip_start_time + datetime.timedelta(seconds=clip_duration)
        
        clip = Clip.objects.create(
            recording=recording, channel_num=0,
            start_index=clip_start_index, length=clip_length,
            start_time=clip_start_time, end_time=clip_end_time,
            creation_time=creation_time)
        
        for name, value in clip_d['annotations'].items():
            info = annotation_infos[name]
            model_utils.annotate_clip(clip, info, value, creation_time)
        

def _get_annotation_names(clips):
    return set().union(*[_get_annotation_names_aux(c) for c in clips])


def _get_annotation_names_aux(clip):
    return set(clip['annotations'].keys())


def _create_annotation_info(name, creation_time):
    return AnnotationInfo.objects.create(
        name=name, type='String', creation_time=creation_time)


def _populate_database(num_clips, query=None, query_period=None):
    
    station = Station.objects.create(
        name='Test Station', time_zone='US/Eastern')
    
    model = DeviceModel.objects.create(
        name='Test Recorder Model', type='Recorder', manufacturer='Nagra',
        model='X')
    
    device = Device.objects.create(
        name='Test Device', model=model, serial_number='0')
    
    station_recorder = StationDevice.objects.create(
        station=station, device=device, start_time=_dt(2017, 3, 1),
        end_time=_dt(2017, 4, 1))
    
    sample_rate = 22050.
    
    clip_duration = 1.
    clip_length = int(round(clip_duration * sample_rate))
    
    num_channels = 1
    recording_length = num_clips * clip_length
    recording_start_time = _dt(2017, 3, 1)
    recording_duration = recording_length / sample_rate
    recording_end_time = \
        recording_start_time + \
        datetime.timedelta(seconds=recording_duration)
            
    # Use same creation time for all objects that have one.
    creation_time = _dt(2017, 4, 1)
    
    recording = Recording.objects.create(
        station_recorder=station_recorder, num_channels=num_channels,
        length=recording_length, sample_rate=sample_rate,
        start_time=recording_start_time, end_time=recording_end_time,
        creation_time=creation_time)

    
    classification = AnnotationInfo.objects.create(
        name='Classification', type='String', creation_time=creation_time)
    
    other = AnnotationInfo.objects.create(
        name='Other', type='String', creation_time=creation_time)

    another = AnnotationInfo.objects.create(
        name='Another', type='String', creation_time=creation_time)
    
    for i in range(num_clips):
        
        if query_period is not None and i != 0 and i % query_period == 0:
            query(i)
            
        clip_start_index = i * clip_length
        offset = clip_start_index / sample_rate
        clip_start_time = \
            recording_start_time + datetime.timedelta(seconds=offset)
        clip_duration = clip_length / sample_rate
        clip_end_time = \
            clip_start_time + datetime.timedelta(seconds=clip_duration)
        
        clip = Clip.objects.create(
            recording=recording, channel_num=0,
            start_index=clip_start_index, length=clip_length,
            start_time=clip_start_time, end_time=clip_end_time,
            creation_time=creation_time)
        
        info = classification if i % 2 == 0 else other

        model_utils.annotate_clip(clip, info, str(i), creation_time)
        
        if i < num_clips / 2:
            model_utils.annotate_clip(clip, another, str(i), creation_time)
            
      
def _depopulate_database():
    
    for station in Station.objects.all():
        station.delete()
        
    for info in AnnotationInfo.objects.all():
        info.delete()
        
    for model in DeviceModel.objects.all():
        model.delete()
