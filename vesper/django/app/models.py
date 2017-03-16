"""Vesper Django model classes."""


import datetime
import os.path

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import (
    BigIntegerField, CASCADE, CharField, DateTimeField, FloatField, ForeignKey,
    IntegerField, ManyToManyField, Model, SET_NULL, TextField)
import pytz

from vesper.django.project.settings import VESPER_CLIPS_DIR_FORMAT
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.vesper_path_utils as vesper_path_utils


def _double(*args):
    return tuple((a, a) for a in args)


class DeviceModel(Model):
     
    name = CharField(max_length=255, unique=True)
    type = CharField(max_length=255)
    manufacturer = CharField(max_length=255)
    model = CharField(max_length=255)
    description = TextField(blank=True)
     
    @property
    def long_name(self):
        return '{} {} {}'.format(self.manufacturer, self.model, self.type)
    
    def __str__(self):
        return self.long_name
     
    class Meta:
        unique_together = ('manufacturer', 'model')
        db_table = 'vesper_device_model'
    
    
class DeviceModelInput(Model):
    
    model = ForeignKey(
        DeviceModel, CASCADE,
        related_name='inputs',
        related_query_name='input')
    local_name = CharField(max_length=255)
    channel_num = IntegerField()
    description = TextField(blank=True)
    
    @property
    def name(self):
        return self.model.name + ' ' + self.local_name
    
    @property
    def long_name(self):
        return self.model.long_name + ' ' + self.local_name
    
    def __str__(self):
        return self.long_name
    
    class Meta:
        unique_together = (('model', 'local_name'), ('model', 'channel_num'))
        db_table = 'vesper_device_model_input'


class DeviceModelOutput(Model):
    
    model = ForeignKey(
        DeviceModel, CASCADE,
        related_name='outputs',
        related_query_name='output')
    local_name = CharField(max_length=255)
    channel_num = IntegerField()
    description = TextField(blank=True)
    
    @property
    def name(self):
        return self.model.name + ' ' + self.local_name
    
    @property
    def long_name(self):
        return self.model.long_name + ' ' + self.local_name
    
    def __str__(self):
        return self.long_name
    
    class Meta:
        unique_together = (('model', 'local_name'), ('model', 'channel_num'))
        db_table = 'vesper_device_model_output'


class Device(Model):
    
    name = CharField(max_length=255, unique=True)
    model = ForeignKey(
        DeviceModel, CASCADE,
        related_name='devices',
        related_query_name='device')
    serial_number = CharField(max_length=255)
    description = TextField(blank=True)
    
    @property
    def long_name(self):
        return self.model.long_name + ' ' + self.serial_number
        
    def __str__(self):
        return self.long_name
    
    class Meta:
        unique_together = ('model', 'serial_number')
        db_table = 'vesper_device'


class DeviceInput(Model):
    
    device = ForeignKey(
        Device, CASCADE,
        related_name='inputs',
        related_query_name='input')
    model_input = ForeignKey(
        DeviceModelInput, CASCADE,
        related_name='device_inputs',
        related_query_name='device_input')
    
    @property
    def local_name(self):
        return self.model_input.local_name
    
    @property
    def name(self):
        return self.device.name + ' ' + self.local_name
    
    @property
    def long_name(self):
        return self.device.long_name + ' ' + self.local_name
    
    @property
    def channel_num(self):
        return self.model_input.channel_num
    
    def __str__(self):
        return self.long_name
    
    class Meta:
        unique_together = ('device', 'model_input')
        db_table = 'vesper_device_input'
        
        
class DeviceOutput(Model):
    
    device = ForeignKey(
        Device, CASCADE,
        related_name='outputs',
        related_query_name='output')
    model_output = ForeignKey(
        DeviceModelOutput, CASCADE,
        related_name='device_outputs',
        related_query_name='device_output')
    
    @property
    def local_name(self):
        return self.model_output.local_name
    
    @property
    def name(self):
        return self.device.name + ' ' + self.local_name
    
    @property
    def long_name(self):
        return self.device.long_name + ' ' + self.local_name
    
    @property
    def channel_num(self):
        return self.model_output.channel_num
    
    def __str__(self):
        return self.long_name
    
    class Meta:
        unique_together = ('device', 'model_output')
        db_table = 'vesper_device_output'
        
        
class DeviceConnection(Model):
    
    output = ForeignKey(
        DeviceOutput, CASCADE,
        related_name='connections',
        related_query_name='connection')
    input = ForeignKey(
        DeviceInput, CASCADE,
        related_name='connections',
        related_query_name='connection')
    start_time = DateTimeField()
    end_time = DateTimeField()
    
    @property
    def name(self):
        return '{} -> {} from {} to {}'.format(
            self.output.name, self.input.name,
            str(self.start_time), str(self.end_time))
    
    @property
    def long_name(self):
        return '{} -> {} from {} to {}'.format(
            self.output.long_name, self.input.long_name,
            str(self.start_time), str(self.end_time))
    
    def __str__(self):
        return self.long_name
        
    class Meta:
        unique_together = ('output', 'input', 'start_time', 'end_time')
        db_table = 'vesper_device_connection'
    
    
_ONE_DAY = datetime.timedelta(days=1)


# Many stations have a fixed location, in which case the location can
# be recorded using the `latitude`, `longitude`, and `elevation` fields
# of the `Station` model. Some stations are mobile, however, so we will
# eventually want to support the storage of station track data. See the
# commented-out `StationTrack` and `StationLocation` models below.
#
# In some cases the sensors of a station will be at different locations,
# and these locations will be used for source localization. In this case
# we will want to track the locations of individual sensors. This could
# be accomplished with `DeviceTrack` and `DeviceLocation` models similar
# to the commented-out `StationTrack` and `StationLocation` models below.
class Station(Model):
    
    name = CharField(max_length=255, unique=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    elevation = FloatField(null=True)
    time_zone = CharField(max_length=255)
    description = TextField(blank=True)
    devices = ManyToManyField(Device, through='StationDevice')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_station'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tz = pytz.timezone(self.time_zone)
        
    @property
    def tz(self):
        return self._tz
    
    def local_to_utc(self, dt, is_dst=None):
        
        """
        Converts a station-local time to UTC.
        
        The time is assumed to be in this station's local time zone,
        regardless of its `tzinfo`, if any.
        """
        
        return time_utils.create_utc_datetime(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
            dt.microsecond, self.tz, is_dst)
        
    def utc_to_local(self, dt):
        
        """
        Converts a UTC time to an aware time with this station's time zone.
        
        The time is assumed to be UTC, regardless of its `tzinfo`, if any.
        """
        
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
            
        return dt.astimezone(self.tz)
    
    def get_midnight_utc(self, date):
        midnight = datetime.datetime(date.year, date.month, date.day)
        return self.local_to_utc(midnight)
    
    def get_noon_utc(self, date):
        noon = datetime.datetime(date.year, date.month, date.day, 12)
        return self.local_to_utc(noon)

    def get_day_interval_utc(self, start_date, end_date=None):
        return _get_interval_utc(start_date, end_date, self.get_midnight_utc)
    
    def get_night_interval_utc(self, start_date, end_date=None):
        return _get_interval_utc(start_date, end_date, self.get_noon_utc)
        
    def get_station_devices(self, device_type, start_time=None, end_time=None):
        
        """
        Gets all station devices of the specified type that were in use
        at this station throughout the specified period.
        """
        
        # The following would seem to be a better way to implement this
        # method (or perhaps obviate it), but unfortunately it raises a
        # django.core.exceptions.FieldError exception with the message
        # "Unsupported lookup 'le' for DateTimeField or join on the field
        # not permitted.". I'm not sure why Django would not support le
        # (or ge) lookups on date/time fields.
        # return StationDevice.objects.filter(
        #    station=self, start_time__le=start_time, end_time__ge=end_time)
    
        return [
            sd for sd in StationDevice.objects.filter(station=self)
            if sd.device.model.type == device_type and \
                    (start_time is None or sd.start_time <= start_time) and \
                    (end_time is None or sd.end_time >= end_time)]
    
    
def _get_interval_utc(start_date, end_date, get_datetime):
    start_time = get_datetime(start_date)
    if end_date is None:
        end_time = start_time + _ONE_DAY
    else:
        end_time = get_datetime(end_date + _ONE_DAY)
    return (start_time, end_time)


class StationDevice(Model):
    
    station = ForeignKey(
        Station, CASCADE,
        related_name='station_devices',
        related_query_name='station_device')
    device = ForeignKey(
        Device, CASCADE,
        related_name='station_devices',
        related_query_name='station_device')
    start_time = DateTimeField()
    end_time = DateTimeField()
    
    @property
    def name(self):
        return '{} at {} from {} to {}'.format(
            self.device.name, self.station.name,
            str(self.start_time), str(self.end_time))
        
    @property
    def long_name(self):
        return '{} at {} from {} to {}'.format(
            self.device.long_name, self.station.name,
            str(self.start_time), str(self.end_time))
        
    def __str__(self):
        return self.long_name
        
    class Meta:
        unique_together = ('station', 'device', 'start_time', 'end_time')
        db_table = 'vesper_station_device'


class Algorithm(Model):
    
    name = CharField(max_length=255, unique=True)
    type = CharField(max_length=255)
    description = TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_algorithm'

    
class AlgorithmVersion(Model):
    
    algorithm = ForeignKey(
        Algorithm, CASCADE,
        related_name='versions',
        related_query_name='version')
    version = CharField(max_length=255)
    description = TextField(blank=True)
    
    @property
    def name(self):
        return self.algorithm.name + ' ' + self.version
    
    @property
    def type(self):
        return self.algorithm.type
    
    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ('algorithm', 'version')
        db_table = 'vesper_algorithm_version'

    
class Processor(Model):
    
    name = CharField(max_length=255, unique=True)
    algorithm_version = ForeignKey(
        AlgorithmVersion, CASCADE,
        related_name='processors',
        related_query_name='processor')
    settings = TextField(blank=True)
    description = TextField(blank=True)
    
    @property
    def type(self):
        return self.algorithm_version.type
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_processor'
        
    
_JOB_LOGS_DIR_PATH = vesper_path_utils.get_archive_dir_path('Logs', 'Jobs')


# A *command* is a specification of something to be executed, possibly
# more than once. A *job* is a particular execution of a command.
#
# The processor of a job can be null since a job may not have a processor,
# for example an archive data import.
#
# The start and end times of a job can also be null, for example if the
# job has been created but has not yet started.
#
# A job may be started by either a user or another job.
class Job(Model):
    
    command = TextField()
    processor = ForeignKey(
        Processor, CASCADE, null=True,
        related_name='jobs',
        related_query_name='job')
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)
    status = CharField(max_length=255)
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, CASCADE, null=True,
        related_name='jobs',
        related_query_name='job')
    creating_job = ForeignKey(
        'Job', CASCADE, null=True,
        related_name='jobs',
        related_query_name='job')
    
    def __str__(self):
        return 'Job {} started {} ended {} command "{}"'.format(
            self.id, self.start_time, self.end_time, self.command)
        
    class Meta:
        db_table = 'vesper_job'
        
    @property
    def log_file_path(self):
        file_name = 'Job {}.log'.format(self.id)
        return os.path.join(_JOB_LOGS_DIR_PATH, file_name)
        
    @property
    def log(self):
        if not os.path.exists(self.log_file_path):
            return ''
        else:
            return os_utils.read_file(self.log_file_path)            
        

# We include the `end_time` field even though it's redundant to accelerate
# queries.
#
# An alternative to making the `recorder` field a `StationDevice` would be
# to have a `station` field that is a `Station` and a `recorder` field
# that is a `Device`. However, the latter introduces a redundancy between
# the recorders indicated in the `StationDevice` table and the recorders
# indicated in the `Recording` table. The former eliminates this redundancy.
class Recording(Model):
    
    station_recorder = ForeignKey(
        StationDevice, CASCADE,
        related_name='recordings',
        related_query_name='recording')
    num_channels = IntegerField()
    length = BigIntegerField()
    sample_rate = FloatField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    creation_time = DateTimeField()
    creating_job = ForeignKey(
        Job, CASCADE, null=True,
        related_name='recordings',
        related_query_name='recording')
    
    @property
    def station(self):
        return self.station_recorder.station
    
    @property
    def recorder(self):
        return self.station_recorder.device
    
    def __str__(self):
        return '{} / {} / {}'.format(
            self.station.name, self.recorder.name, self.start_time)
        
    class Meta:
        unique_together = ('station_recorder', 'start_time')
        db_table = 'vesper_recording'
        
        
class RecordingFile(Model):
    
    recording = ForeignKey(
        Recording, CASCADE,
        related_name='files',
        related_query_name='file')
    file_num = IntegerField()
    start_index = BigIntegerField()
    length = BigIntegerField()
    path = CharField(max_length=255, unique=True, null=True)
    
    def __str__(self):
        r = self.recording
        return '{} / File {} / "{}"'.format(
            str(r), self.file_num, self.path)
        
    class Meta:
        unique_together = ('recording', 'file_num')
        db_table = 'vesper_recording_file'
        
        
    @property
    def sample_rate(self):
        return self.recording.sample_rate
    
    
    @property
    def duration(self):
        return signal_utils.get_duration(self.length, self.sample_rate)


# The station, recorder, and sample rate of a clip are the station,
# recorder, and sample rate of its recording.
#
# Ideally, and in most cases moving forward, we will know the start index
# of a clip in its parent recording. However, there are many clips that
# people have collected for which the start time of a clip is known but
# not its start index in the parent recording, either because the parent
# recording was not retained or because the detector that created the
# clip (e.g. the Old Bird Tseep or Thrush detector) was designed to save
# the start time (perhaps as an elapsed time from the start of the
# recording) but not the start index. For such clips we allow the
# start index to be null. We require, however, that every clip have
# a start time.
#
# The `end_time` field of a clip is redundant, since it can be computed
# from the clip's start time, length, and sample rate. We include it anyway
# to accelerate certain types of queries. For example, we will want to be
# able to find all of the clips whose time intervals intersect a specified
# recording subinterval.
#
# We used to include a multi-column unique constraint to prevent duplicate
# clips from being created by accidentally running a particular detector on
# a particular recording more than once. I decided to eliminate this
# constraint since such accidents can be recovered from by deleting the
# redundant detector job (the job's clips will be deleted by the
# database's cascade feature). I plan to provide some sort of system
# for defining workflows and keeping track of which workflow tasks
# have been performed on which recordings, and this should help prevent
# redundant detector runs.
#
# Sometimes we know the processor that created a clip, but there is no
# corresponding job, as when we import clips that were detected outside
# of Vesper. In this case the processor of the clip is non-null, but the
# job is null. When both are non-null, the processor of the clip and the
# processor of the job should be the same.
#
# At least for the time being, we require that every clip refer to a
# recording for which the station, recorder, number of channels, start
# time, and length are known. Thus we do not support clips for which
# some of this recording information (usually the start time and length)
# are not accurately known. If supporting such clips turns out to be
# of great importance, perhaps we can allow null recording lengths,
# and add flags that indicate whether or not recording start and end
# times are only approximate.
class Clip(Model):
    
    recording = ForeignKey(
        Recording, CASCADE,
        related_name='clips',
        related_query_name='clip')
    channel_num = IntegerField()
    start_index = BigIntegerField(null=True)
    length = BigIntegerField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, CASCADE, null=True,
        related_name='clips',
        related_query_name='clip')
    creating_job = ForeignKey(
        Job, CASCADE, null=True,
        related_name='clips',
        related_query_name='clip')
    creating_processor = ForeignKey(
        Processor, CASCADE, null=True,
        related_name='clips',
        related_query_name='clip')
    
    def __str__(self):
        return '{} / {} / Channel {} / {}'.format(
            self.station.name, self.recorder.name, self.channel_num,
            self.start_time)
        
    class Meta:
        db_table = 'vesper_clip'
        
    @property
    def station(self):
        return self.recording.station
    
    @property
    def recorder(self):
        return self.recording.recorder
    
    @property
    def sample_rate(self):
        return self.recording.sample_rate
    
    @property
    def wav_file_contents(self):
        with open(self.wav_file_path, 'rb') as file_:
            return file_.read()
        
    @property
    def wav_file_path(self):
        return _create_clip_file_path(self.id)
        
    @property
    def wav_file_url(self):
        return reverse('clip-wav', args=(self.id,))            


def _create_clip_file_path(clip_id):
    id_parts = _get_clip_id_parts(clip_id, VESPER_CLIPS_DIR_FORMAT)
    path_parts = id_parts[:-1]
    id_ = ' '.join(id_parts)
    file_name = 'Clip {}.wav'.format(id_)
    path_parts.append(file_name)
    return vesper_path_utils.get_archive_dir_path('Clips', *path_parts)


def _get_clip_id_parts(num, format_):
    
    # Format number as digit string with leading zeros.
    num_digits = sum(format_)
    f = '{:0' + str(num_digits) + 'd}'
    digits = f.format(num)
    
    # Split string into parts.
    i = 0
    parts = []
    for num_digits in format_:
        parts.append(digits[i:i + num_digits])
        i += num_digits
        
    return parts
    
    
# Note that one might implement annotation value constraints as presets.
# We choose not to do so, however, since the constraints provide important
# information regarding the annotation values in the archive. We reserve
# presets for UI configuration information that does not help describe
# archive contents.
class AnnotationConstraint(Model):
    
    name = CharField(max_length=255, unique=True)
    description = TextField(blank=True)
    text = TextField(blank=True)
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, CASCADE, null=True,
        related_name='annotation_constraints',
        related_query_name='annotation_constraint')
    creating_job = ForeignKey(
        Job, CASCADE, null=True,
        related_name='annotation_constraints',
        related_query_name='annotation_constraint')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_annotation_constraint'
    
    
class AnnotationInfo(Model):
    
    TYPE_STRING = 'String'
    TYPE_CHOICES = ((TYPE_STRING, TYPE_STRING),)
    
    name = CharField(max_length=255, unique=True)
    description = TextField(blank=True)
    type = CharField(max_length=255, choices=TYPE_CHOICES)
    constraint = ForeignKey(
        AnnotationConstraint, null=True, on_delete=SET_NULL,
        related_name='annotation_infos',
        related_query_name='annotation_info')
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, CASCADE, null=True,
        related_name='annotation_infos',
        related_query_name='annotation_info')
    creating_job = ForeignKey(
        Job, CASCADE, null=True,
        related_name='annotation_infos',
        related_query_name='annotation_info')
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_annotation_info'

    
class StringAnnotation(Model):
    
    clip = ForeignKey(
        Clip, CASCADE,
        related_name='string_annotations',
        related_query_name='string_annotation')
    info = ForeignKey(
        AnnotationInfo, CASCADE,
        related_name='string_annotations',
        related_query_name='string_annotation')
    value = CharField(max_length=255)
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, CASCADE, null=True,
        related_name='string_annotations',
        related_query_name='string_annotation')
    creating_job = ForeignKey(
        Job, CASCADE, null=True,
        related_name='string_annotations',
        related_query_name='string_annotation')
    creating_processor = ForeignKey(
        Processor, CASCADE, null=True,
        related_name='string_annotations',
        related_query_name='string_annotations')
    
    class Meta:
        unique_together = ('clip', 'info')
        db_table = 'vesper_string_annotation'
    
    
# class StringAnnotationEdit(Model):
#      
#     ACTION_SET = 'S'
#     ACTION_DELETE = 'D'
#     ACTION_CHOICES = (
#         (ACTION_SET, 'Set'),
#         (ACTION_DELETE, 'Delete'))
#      
#     clip = ForeignKey(
#         Clip, CASCADE,
#         related_name='string_annotation_edits',
#         related_query_name='string_annotation_edit')
#     info = ForeignKey(
#         AnnotationInfo, CASCADE,
#         related_name='string_annotation_edits',
#         related_query_name='string_annotation_edit')
#     action = CharField(max_length=1, choices=ACTION_CHOICES)
#     value = CharField(max_length=255)
#     creation_time = DateTimeField()
#     creating_user = ForeignKey(
#         User, CASCADE, null=True,
#         related_name='string_annotation_edits',
#         related_query_name='string_annotation_edit')
#     creating_job = ForeignKey(
#         Job, CASCADE, null=True,
#         related_name='string_annotation_edits',
#         related_query_name='string_annotation_edit')
#     creating_processor = ForeignKey(
#         Processor, CASCADE, null=True,
#         related_name='string_annotation_edits',
#         related_query_name='string_annotation_edits')
#
#     class Meta:
#         db_table = 'vesper_string_annotation_edit'


# class RecordingJob(Model):
#     
#     recording = ForeignKey(
#         Recording, CASCADE,
#         related_name='recording_jobs',
#         related_query_name='recording_job')
#     job = ForeignKey(
#         Job, CASCADE,
#         related_name='recording_jobs',
#         related_query_name='recording_job')
#     
#     def __str__(self):
#         return '{} {}'.format(str(self.recording), self.job.processor.name)
#     
#     class Meta:
#         unique_together = ('recording', 'job')
#         db_table = 'vesper_recording_job'
        
    
'''
We might use tables like the following to keep track of which processors
have been run on which recordings and clips. This information could help
make it easy for users to, say, identify recordings to run a detector on
or clips to run a classifier on.

class RecordingJob(Model):
    recording = ForeignKey(
        Recording, CASCADE,
        related_name='recording_jobs',
        related_query_name='recording_job')
    job = ForeignKey(
        Job, CASCADE,
        related_name='recording_jobs',
        related_query_name='recording_job')
    
# The following gets the recordings on which a certain processor has
# not been run. It's more complicated than I'd like, but I haven't
# been able to figure out anything simpler. It's a problem that the
# set of excluded recordings could be large, and the analogous
# problem for clips is even worse. It might help to alleviate the
# problem to limit the time period of the query.
recording_jobs = RecordingJob.objects.filter(
    job__processor=processor).select_related('recording')
excluded_recordings = frozenset(rj.recording for rj in recording_jobs)
recordings = Recording.objects.exclude(pk__in=excluded_recordings)

# The time-limited query would be as below.
recording_jobs = RecordingJob.objects.filter(
    job__processor=processor,
    recording__start_time__range=start_time_range).select_related('recording')
excluded_recordings = frozenset(rj.recording for rj in recording_jobs)
recordings = Recording.objects.filter(
    start_time__range=start_time_range).exclude(
        pk__in=excluded_recordings)
'''
