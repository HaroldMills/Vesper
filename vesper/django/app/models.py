import datetime
import logging
import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import (
    BigIntegerField, CASCADE, CharField, DateTimeField, FloatField, ForeignKey,
    IntegerField, ManyToManyField, Model, TextField)
import pytz

import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
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
    
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='inputs')
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
    
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='outputs')
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


# class DeviceModelSetting(Model):
#       
#     model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='settings')
#     local_name = CharField(max_length=255)
#     description = TextField(blank=True)
#       
#     @property
#     def name(self):
#         return self.model.name + ' ' + self.local_name
#     
#     @property
#     def long_name(self):
#         return self.model.long_name + ' ' + self.local_name
#     
#     def __str__(self):
#         return self.long_name
#     
#     class Meta:
#         unique_together = ('model', 'local_name')
#         db_table = 'vesper_device_model_setting'
        
        
class Device(Model):
    
    name = CharField(max_length=255, unique=True)
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='devices')
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
    
    device = ForeignKey(Device, on_delete=CASCADE, related_name='inputs')
    model_input = ForeignKey(
        DeviceModelInput, on_delete=CASCADE, related_name='device_inputs')
    
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
        Device, on_delete=CASCADE, related_name='outputs')
    model_output = ForeignKey(
        DeviceModelOutput, on_delete=CASCADE, related_name='device_outputs')
    
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
        
        
# class DeviceSetting(Model):
#      
#     device = ForeignKey(Device, on_delete=CASCADE, related_name='settings')
#     model_setting = ForeignKey(
#         DeviceModelSetting, on_delete=CASCADE, related_name='instances')
#     value = CharField(max_length=255)
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#      
#     @property
#     def local_name(self):
#         return self.model_setting.local_name
#     
#     @property
#     def name(self):
#         return self.device.name + ' ' + self.local_name
#     
#     @property
#     def long_name(self):
#         return self.device.long_name + ' ' + self.local_name
#     
#     def __str__(self):
#         return self.long_name
#     
#     class Meta:
#         unique_together = (
#             'device', 'model_setting', 'value', 'start_time', 'end_time')
#         db_table = 'vesper_device_setting'
    
    
class DeviceConnection(Model):
    
    output = ForeignKey(
        DeviceOutput, on_delete=CASCADE, related_name='connections')
    input = ForeignKey(
        DeviceInput, on_delete=CASCADE, related_name='connections')
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
    
    
# class RecorderChannelAssignment(Model):
#     
#     recorder = ForeignKey(
#         Device, on_delete=CASCADE, related_name='channel_assignments')
#     input = ForeignKey(
#         DeviceInput, on_delete=CASCADE, related_name='channel_assignments')
#     channel_num = IntegerField()
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     
#     @property
#     def name(self):
#         return '{} -> {} from {} to {}'.format(
#             self.input.name, self.channel_num,
#             str(self.start_time), str(self.end_time))
#     
#     @property
#     def long_name(self):
#         return '{} -> {} from {} to {}'.format(
#             self.input.long_name, self.channel_num,
#             str(self.start_time), str(self.end_time))
#     
#     def __str__(self):
#         return self.long_name
#         
#     class Meta:
#         unique_together = (
#             'recorder', 'input', 'channel_num', 'start_time', 'end_time')
#         db_table = 'vesper_recorder_channel_assignment'
    
    
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
        
    def get_station_devices(self, device_type, start_time, end_time):
        
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
                    sd.start_time <= start_time and \
                    sd.end_time >= end_time]
    
    
def _get_interval_utc(start_date, end_date, get_datetime):
    start_time = get_datetime(start_date)
    if end_date is None:
        end_time = start_time + _ONE_DAY
    else:
        end_time = get_datetime(end_date + _ONE_DAY)
    return (start_time, end_time)


# The `StationTrack` and `StationLocation` models will store tracks of mobile
# stations. When we want the location of a station at a specified time, we
# can look first for a `StationTrack` whose time interval includes that time,
# and if there is no such track we can fall back on the location from the
# `Station` model (if that location is specified). The `Station` model might
# also have a boolean `mobile` field to tell us whether or not to look for
# tracks before looking for the `Station` location.
# class StationTrack(Model):
#     station = ForeignKey(Station, on_delete=CASCADE, related_name='tracks')
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     class Meta:
#         db_table = 'vesper_station_track'
# 
#     
# class StationLocation(Model):
#     track = ForeignKey(
#         StationTrack, on_delete=CASCADE, related_name='locations')
#     latitude = FloatField()
#     longitude = FloatField()
#     elevation = FloatField(null=True)
#     time = DateTimeField()
#     class Meta:
#         db_table = 'vesper_station_location'
    
    
class StationDevice(Model):
    
    station = ForeignKey(
        Station, on_delete=CASCADE, related_name='station_devices')
    device = ForeignKey(
        Device, on_delete=CASCADE, related_name='station_devices')
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
        Algorithm, on_delete=CASCADE, related_name='versions')
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
        AlgorithmVersion, on_delete=CASCADE, related_name='processors')
    settings = TextField(blank=True)
    description = TextField(blank=True)
    
    @property
    def type(self):
        return self.algorithm_version.type
    
    def __str__(self):
        return self.name
    
    class Meta:
        db_table = 'vesper_processor'
        
    
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
        Processor, null=True, on_delete=CASCADE, related_name='jobs')
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)
    status = CharField(max_length=255)
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='jobs')
    creating_job = ForeignKey(
        'Job', null=True, on_delete=CASCADE, related_name='jobs')
    
    def __str__(self):
        return 'Job {} started {} ended {} command "{}"'.format(
            self.id, self.start_time, self.end_time, self.command)
        
    class Meta:
        db_table = 'vesper_job'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._logger = None
        
    @property
    def log_file_path(self):
        dir_path = _get_job_logs_dir_path()
        file_name = 'Job {}.log'.format(self.id)
        return os.path.join(dir_path, file_name)
        
    @property
    def logger(self):
        if self._logger is None:
            self._logger = self._create_logger()
        return self._logger
    
    def _create_logger(self):
        
        _create_job_logs_dir_if_needed()
        
        logger_name = 'Job {}'.format(self.id)
        logger = logging.getLogger(logger_name)
        
        level = 'INFO' if settings.DEBUG else 'INFO'
        file_path = self.log_file_path
        
        config = {
            'version': 1,
            'formatters': {
                'vesper': {
                    'class': 'logging.Formatter',
                    'format': '%(asctime)s %(levelname)-8s %(message)s'
                }
            },
            'handlers': {
                'console': {
                    'class': 'logging.StreamHandler',
                    'level': level,
                    'formatter': 'vesper'
                },
                'file': {
                    'class': 'logging.FileHandler',
                    'filename': file_path,
                    'mode': 'w',
                    'level': level,
                    'formatter': 'vesper'
                }
            },
            'loggers': {
                logger_name: {
                    'handlers': ['console', 'file'],
                    'level': level,
                }
            }
        }
        
        logging.config.dictConfig(config)
        
        return logger
    
    
    @property
    def log(self):
        return os_utils.read_file(self.log_file_path)
        

_job_logs_dir_path = None


def _get_job_logs_dir_path():
    
    global _job_logs_dir_path
    
    if _job_logs_dir_path is None:
        _job_logs_dir_path = vesper_path_utils.get_path('Logs', 'Jobs')
            
    return _job_logs_dir_path


def _create_job_logs_dir_if_needed():
    dir_path = _get_job_logs_dir_path()
    os_utils.create_directory(dir_path)
    
    
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
        StationDevice, on_delete=CASCADE, related_name='recordings')
    num_channels = IntegerField()
    length = BigIntegerField()
    sample_rate = FloatField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    creation_time = DateTimeField()
    creating_job = ForeignKey(
        Job, null=True, on_delete=CASCADE, related_name='recordings')
    
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
    
    recording = ForeignKey(Recording, on_delete=CASCADE, related_name='files')
    file_num = IntegerField()
    start_index = BigIntegerField()
    length = BigIntegerField()
    file_path = CharField(max_length=255, unique=True, null=True)
    
    def __str__(self):
        r = self.recording
        return 'Recording "{}" "{}" {} File {} "{}"'.format(
            r.station.name, r.recorder.name,
            r.start_time, self.file_num, self.file_path)
        
    class Meta:
        unique_together = ('recording', 'file_num')
        db_table = 'vesper_recording_file'


# class RecorderModel(Model):
#     
#     name = CharField(max_length=255, unique=True)
#     manufacturer = CharField(max_length=255)
#     model = CharField(max_length=255)
#     num_channels = IntegerField()
#     description = TextField(blank=True)
#      
#     @property
#     def long_name(self):
#         return '{} {} Recorder'.format(self.manufacturer, self.model)
#     
#     def __str__(self):
#         return self.long_name
#      
#     class Meta:
#         unique_together = ('manufacturer', 'model')
#         db_table = 'vesper_recorder_model'
# 
# 
# class RecorderModelChannel(Model):
#     
#     model = ForeignKey(
#         RecorderModel, on_delete=CASCADE, related_name='channels')
#     num = IntegerField()
# 
# 
# class Recorder(Model):
#     
#     name = CharField(max_length=255, unique=True)
#     model = ForeignKey(
#         RecorderModel, on_delete=CASCADE, related_name='recorders')
#     serial_number = CharField(max_length=255)
#     description = TextField(blank=True)
#     
#     @property
#     def num_channels(self):
#         return self.model.num_channels
#     
#     @property
#     def long_name(self):
#         return self.model.long_name + ' ' + self.serial_number
#         
#     def __str__(self):
#         return self.long_name
#     
#     class Meta:
#         unique_together = ('model', 'serial_number')
#         db_table = 'vesper_recorder'
# 
#     
# class RecorderChannel(Model):
#     
#     recorder = ForeignKey(Recorder, on_delete=CASCADE, related_name='channels')
#     model_channel = ForeignKey(
#         RecorderModelChannel, on_delete=CASCADE,
#         related_name='recorder_channels')
# 
# 
# class MicrophoneModel(Model):
#     
#     name = CharField(max_length=255, unique=True)
#     manufacturer = CharField(max_length=255)
#     model = CharField(max_length=255)
#     description = TextField(blank=True)
#      
#     @property
#     def long_name(self):
#         return '{} {} Microphone'.format(self.manufacturer, self.model)
#     
#     def __str__(self):
#         return self.long_name
#      
#     class Meta:
#         unique_together = ('manufacturer', 'model')
#         db_table = 'vesper_microphone_model'
# 
# 
# class MicrophoneModelOutput(Model):
#     
#     local_name = CharField(max_length=255, blank=True)
#     model = ForeignKey(
#         MicrophoneModel, on_delete=CASCADE, related_name='outputs')
#     channel_num = IntegerField()
#     description = TextField(blank=True)
#     
#     
# class Microphone(Model):
#     
#     name = CharField(max_length=255, unique=True)
#     model = ForeignKey(
#         MicrophoneModel, on_delete=CASCADE, related_name='microphones')
#     serial_number = CharField(max_length=255)
#     description = TextField(blank=True)
#     
#     @property
#     def long_name(self):
#         return self.model.long_name + ' ' + self.serial_number
#         
#     def __str__(self):
#         return self.long_name
#     
#     class Meta:
#         unique_together = ('model', 'serial_number')
#         db_table = 'vesper_microphone'
# 
#     
# class MicrophoneOutput(Model):
#     
#     microphone = ForeignKey(
#         Microphone, on_delete=CASCADE, related_name='outputs')
#     model_output = ForeignKey(
#         MicrophoneModelOutput, on_delete=CASCADE,
#         related_name='microphone_outputs')
#     
#     
# class StationRecorder(Model):
#     
#     station = ForeignKey(
#         Station, on_delete=CASCADE, related_name='station_recorders')
#     recorder = ForeignKey(
#         Recorder, on_delete=CASCADE, related_name='station_recorders')
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     
#     @property
#     def name(self):
#         return '{} at {} from {} to {}'.format(
#             self.recorder.name, self.station.name,
#             str(self.start_time), str(self.end_time))
#         
#     @property
#     def long_name(self):
#         return '{} at {} from {} to {}'.format(
#             self.recorder.long_name, self.station.name,
#             str(self.start_time), str(self.end_time))
#         
#     def __str__(self):
#         return self.long_name
#         
#     class Meta:
#         unique_together = ('station', 'recorder', 'start_time', 'end_time')
#         db_table = 'vesper_station_recorder'
# 
# 
# class RecorderMicrophoneConnection(Model):
#     
#     recorder_channel = ForeignKey(
#         RecorderChannel, on_delete=CASCADE, related_name='connections')
#     microphone_output = ForeignKey(
#         MicrophoneOutput, on_delete=CASCADE, related_name='connections')
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     
#     
# class RecorderMicrophone(Model):
#     
#     recorder = ForeignKey(
#         Recorder, on_delete=CASCADE, related_name='recorder_microphones')
#     channel_num = IntegerField()
#     microphone = ForeignKey(
#         Microphone, on_delete=CASCADE, related_name='recorder_microphones')
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     
#     @property
#     def name(self):
#         return '{} in {} channel {} from {} to {}'.format(
#             self.microphone.name, self.recorder.name, self.channel_num,
#             str(self.start_time), str(self.end_time))
#         
#     @property
#     def long_name(self):
#         return '{} in {} channel {} from {} to {}'.format(
#             self.microphone.long_name, self.recorder.name, self.channel_num,
#             str(self.start_time), str(self.end_time))
#         
#     def __str__(self):
#         return self.long_name
#         
#     class Meta:
#         unique_together = \
#             ('recorder', 'channel_num', 'microphone', 'start_time', 'end_time')
#         db_table = 'vesper_recorder_microphone'

    
# The station, recorder, and sample rate of a clip are the station,
# recorder, and sample rate of its recording.
#
# The `end_time` field of a clip is redundant, since it can be computed
# from the clip's start time, length, and sample rate. We include it anyway
# to accelerate certain types of queries. For example, we will want to be
# able to find all of the clips whose time intervals intersect a specified
# recording subinterval.
#
# The `file_path` field of a clip should be `None` if and only if the clip
# samples are available as part of the clip's recording, and the clip is not
# itself stored in its own file. In some cases the samples of a clip may be
# available both as part of the clip's recording and in an extracted clip
# file. In this case the `file_path` field should be the path of the extracted
# clip file.
#
# We include a multi-column unique constraint to prevent duplicate clips
# from being created by accidentally running a particular detector on a
# particular recording more than once.
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
    
    recording = ForeignKey(Recording, on_delete=CASCADE, related_name='clips')
    channel_num = IntegerField()
    start_index = BigIntegerField(null=True)
    length = BigIntegerField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='clips')
    creating_job = ForeignKey(
        Job, null=True, on_delete=CASCADE, related_name='clips')
    creating_processor = ForeignKey(
        Processor, null=True, on_delete=CASCADE, related_name='clips')
    file_path = CharField(max_length=255, unique=True, null=True)
    
    def __str__(self):
        return '{} / {} / {} / {}'.format(
            self.station.name, self.recorder.name, self.channel_num,
            self.start_time)
        
    class Meta:
        unique_together = (
            'recording', 'channel_num', 'start_time', 'length',
            'creating_processor')
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
        # TODO: Handle errors, e.g. no such file.
        with open(self.wav_file_path, 'rb') as file_:
            return file_.read()
        
    @property
    def wav_file_path(self):
        if self.file_path is None:
            return _create_clip_file_path(self)
        else:
            return self.file_path
        
    @property
    def wav_file_url(self):
        return reverse('clip-wav', args=(self.id,))


# TODO: Don't hard code this.
_CLIPS_DIR_FORMAT = (3, 3)


def _create_clip_file_path(clip):
    id_parts = _get_clip_id_parts(clip.id, _CLIPS_DIR_FORMAT)
    path_parts = id_parts[:-1]
    id_ = ' '.join(id_parts)
    file_name = 'Clip {}.wav'.format(id_)
    path_parts.append(file_name)
    return vesper_path_utils.get_path('Clips', *path_parts)


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
    
    
class Annotation(Model):
    
    clip = ForeignKey(Clip, on_delete=CASCADE, related_name='annotations')
    name = CharField(max_length=255)      # e.g. 'Classification', 'Outside'
    value = TextField(blank=True)         # e.g. 'NFC.AMRE', 'True'
    creation_time = DateTimeField(null=True)
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='annotations')
    creating_job = ForeignKey(
        Job, null=True, on_delete=CASCADE, related_name='annotations')
    
    def __str__(self):
        return '({}, {})'.format(self.name, self.value)
    
    class Meta:
        unique_together = ('clip', 'name')
        db_table = 'vesper_annotation'


class RecordingJob(Model):
    
    recording = ForeignKey(
        Recording, on_delete=CASCADE, related_name='recording_jobs')
    job = ForeignKey(Job, on_delete=CASCADE, related_name='recording_jobs')
    
    def __str__(self):
        return '{} {}'.format(str(self.recording), self.job.processor.name)
    
    class Meta:
        unique_together = ('recording', 'job')
        db_table = 'vesper_recording_job'
        
    
'''
We might use tables like the following to keep track of which processors
have been run on which recordings and clips. This information could help
make it easy for users to, say, identify recordings to run a detector on
or clips to run a classifier on.

class RecordingJob(Model):
    recording = ForeignKey(
        Recording, on_delete=CASCADE, related_name='recording_jobs')
    job = ForeignKey(Job, on_delete=CASCADE, related_name='recording_jobs')
    
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
