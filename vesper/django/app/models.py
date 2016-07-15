import logging
import os.path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db.models import (
    BigIntegerField, CASCADE, CharField, DateTimeField, FloatField, ForeignKey,
    IntegerField, ManyToManyField, Model, SET_NULL, TextField)

import vesper.util.os_utils as os_utils


def _double(*args):
    return tuple((a, a) for a in args)


class DeviceModel(Model):
    manufacturer = CharField(max_length=255)
    model = CharField(max_length=255)
    type = CharField(max_length=255)
    short_name = CharField(max_length=255, blank=True)
    description = TextField(blank=True)
    def __str__(self):
        return '{} {} {}'.format(self.manufacturer, self.model, self.type)
    class Meta:
        unique_together = ('manufacturer', 'model')
        db_table = 'vesper_device_model'
    
    
class DeviceModelInput(Model):
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='inputs')
    name = CharField(max_length=255)
    description = TextField(blank=True)
    def __str__(self):
        return self.name
    class Meta:
        unique_together = ('model', 'name')
        db_table = 'vesper_device_model_input'


class DeviceModelOutput(Model):
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='outputs')
    name = CharField(max_length=255)
    description = TextField(blank=True)
    def __str__(self):
        return self.name
    class Meta:
        unique_together = ('model', 'name')
        db_table = 'vesper_device_model_output'


class DeviceModelSetting(Model):
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='settings')
    name = CharField(max_length=255)
    description = TextField(blank=True)
    class Meta:
        unique_together = ('model', 'name')
        db_table = 'vesper_device_model_setting'
        
        
class Device(Model):
    model = ForeignKey(DeviceModel, on_delete=CASCADE, related_name='instances')
    serial_number = CharField(max_length=255)
    name = CharField(max_length=255, blank=True)
    description = TextField(blank=True)
    def __str__(self):
        return str(self.model) + ' ' + self.serial_number
    class Meta:
        unique_together = ('model', 'serial_number')
        db_table = 'vesper_device'


class DeviceInput(Model):
    model_input = ForeignKey(
        DeviceModelInput, on_delete=CASCADE, related_name='instances')
    device = ForeignKey(Device, on_delete=CASCADE, related_name='inputs')
    def __str__(self):
        return self.model_input.name
    class Meta:
        unique_together = ('model_input', 'device')
        db_table = 'vesper_device_input'
        
        
class DeviceOutput(Model):
    model_output = ForeignKey(
        DeviceModelOutput, on_delete=CASCADE, related_name='instances')
    device = ForeignKey(Device, on_delete=CASCADE, related_name='outputs')
    def __str__(self):
        return self.model_output.name
    class Meta:
        unique_together = ('model_output', 'device')
        db_table = 'vesper_device_output'
        
        
class DeviceConnection(Model):
    output = ForeignKey(
        DeviceOutput, on_delete=CASCADE, related_name='connections')
    input = ForeignKey(
        DeviceInput, on_delete=CASCADE, related_name='connections')
    start_time = DateTimeField()
    end_time = DateTimeField()
    def __str__(self):
        return('{} {} -> {} {} from {} to {}'.format(
            str(self.output.device), str(self.output),
            str(self.input.device), str(self.input),
            str(self.start_time), str(self.end_time)))
    class Meta:
        db_table = 'vesper_device_connection'
    
    
class RecorderChannelAssignment(Model):
    recorder = ForeignKey(
        Device, on_delete=CASCADE, related_name='channel_assignments')
    input_name = CharField(max_length=255)
    channel_num = IntegerField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    class Meta:
        db_table = 'vesper_recorder_channel_assignment'
    
    
class DeviceSetting(Model):
    model_setting = ForeignKey(
        DeviceModelSetting, on_delete=CASCADE, related_name='instances')
    device = ForeignKey(Device, on_delete=CASCADE, related_name='settings')
    value = CharField(max_length=255)
    start_time = DateTimeField()
    end_time = DateTimeField()
    class Meta:
        db_table = 'vesper_device_setting'
    
    
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
    description = TextField(blank=True)
    latitude = FloatField(null=True)
    longitude = FloatField(null=True)
    elevation = FloatField(null=True)
    time_zone = CharField(max_length=255)
    devices = ManyToManyField(Device, through='StationDevice')
    def __str__(self):
        return '{} {} {} {} {}'.format(
            self.name, self.latitude, self.longitude, self.elevation,
            self.time_zone)
    class Meta:
        db_table = 'vesper_station'
    
    
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
        Station, on_delete=CASCADE, related_name='device_associations')
    device = ForeignKey(
        Device, on_delete=CASCADE, related_name='station_associations')
    start_time = DateTimeField()
    end_time = DateTimeField()
    def __str__(self):
        return '{} at {} from {} to {}'.format(
            str(self.device), self.station.name, self.start_time, self.end_time)
    class Meta:
        db_table = 'vesper_station_device'


class Algorithm(Model):
    type = CharField(max_length=255)
    name = CharField(max_length=255)
    version = CharField(max_length=255)
    description = TextField(blank=True)
    def __str__(self):
        return 'Algorithm "{}" "{}" "{}"'.format(
            self.type, self.name, self.version)
    class Meta:
        db_table = 'vesper_algorithm'
    
    
class Bot(Model):
    name = CharField(max_length=255)
    description = TextField(blank=True)
    algorithm = ForeignKey(Algorithm, on_delete=CASCADE, related_name='bots')
    settings = TextField(blank=True)
    def __str__(self):
        return 'Bot "{}" algorithm {} settings "{}"'.format(
            self.name, str(self.algorithm), self.self.settings)
    class Meta:
        db_table = 'vesper_bot'
        
    
class Job(Model):
    
    command = TextField()
    creation_time = DateTimeField()
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='jobs')
    creating_job = ForeignKey(
        'Job', null=True, on_delete=CASCADE, related_name='jobs')
    bot = ForeignKey(Bot, null=True, on_delete=CASCADE, related_name='jobs')
    start_time = DateTimeField(null=True)
    end_time = DateTimeField(null=True)
    status = CharField(max_length=255)
    
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
        _job_logs_dir_path = \
            os.path.join(settings.VESPER_DATA_DIR, 'Logs', 'Jobs')
            
    return _job_logs_dir_path


def _create_job_logs_dir_if_needed():
    dir_path = _get_job_logs_dir_path()
    os_utils.create_directory(dir_path)
    
    
# We include an end time field even though it's redundant to accelerate queries.
class Recording(Model):
    station = ForeignKey(Station, on_delete=CASCADE, related_name='recordings')
    recorder = ForeignKey(Device, on_delete=CASCADE, related_name='recordings')
    num_channels = IntegerField()
    length = BigIntegerField()
    sample_rate = FloatField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    def __str__(self):
        return 'Recording "{}" "{}" {} {} {} {}'.format(
            self.station.name, str(self.recorder), self.num_channels,
            self.length, self.sample_rate, self.start_time)
    class Meta:
        db_table = 'vesper_recording'
        
        
class RecordingFile(Model):
    recording = ForeignKey(Recording, on_delete=CASCADE, related_name='files')
    file_num = IntegerField()
    start_index = BigIntegerField()
    length = BigIntegerField()
    imported_file_path = CharField(max_length=255, null=True) # long enough?
    file_path = CharField(max_length=255, unique=True, null=True) # long enough?
    class Meta:
        db_table = 'vesper_recording_file'


# The station and recorder of a clip must always be specified. I don't
# think this will be a problem since people almost always know where
# their data came from. One could create a special "Unknown" station
# or recorder if needed.
#
# One can have no knowledge, partial knowledge, or complete knowledge
# of the parent recording of a clip. For example, if one ran a detector
# years ago on live audio input that was not saved, and one didn't
# record when monitoring started and ended, or if for whatever reason
# one cannot locate the recording from which a clip came, one may have
# no knowledge of the parent recording. In this case the `recording`,
# `channel_num`, and `start_index` fields of a clip can be `None`.
#
# In other cases one might know when monitoring started and ended for
# each station and night, but one might not have saved the audio samples
# themselves. Or, one might have the recordings but not want to store
# them on a server. In this case an archive will contain recording
# metadata but not the audio samples. The recording metadata are stored
# in a `Recording` object, but there are no corresponding `RecordingFile`
# objects. The `recording` and `channel_num` fields of a clip from such
# a recording will not be `None`. The `start_index` field of a clip from
# such a recording may or may not be `None`, according to whether or not
# the exact start index of the clip in the recording is known.
#
# A recording whose samples are archived will have both a `Recording`
# object and associated `RecordingFile` objects in an archive.
#
# When the metadata for a clip's recording are available (regardless of
# whether or not the recording's audio samples are available), the
# `station` and `recorder` fields of the clip are redundant since both
# are also available via the recording. We require them anyway for
# consistency with the case when a recording's metadata are not available.
#
# The `length`, `sample_rate`, `start_time`, and `end_time` fields of a
# `Clip` object must always be set. The `sample_rate` field is redundant
# since it can always be obtained either from the parent recording of a
# clip or from the clip's sound file. We include it, however, to accelerate
# certain types of queries, especially ones that would otherwise require
# accessing a clip's sound file. Given that the sample rate is available
# the `end_time` field is also redundant, but we include it anyway to
# accelerate certain types of queries. For example, we will want to be
# able to find all of the clips whose time intervals intersect a specified
# recording subinterval.
#
# The `file_path` field of a `Clip` object should be `None` if and only
# if the clip samples are available as part of the clip's recording, and
# the clip is not itself stored in its own file. In some cases the samples
# of a clip may be available both as part of the clip's recording and in
# an extracted clip file. In this case the `file_path` field should be
# set to the path of the extracted clip file.
#
# A concise (but redundant, given the above) summary of field redundancies:
#
# * The redundant `station` and `recorder` fields are included to support
#   the common case of orphaned clips.
#
# * The redundant `sample_rate` field is included to accelerate certain
#   types of queries.
#
# * The redundant `end_time` field is included to accelerate certain types
#   of interval queries.
#
# TODO: Add `creator` field with the creating agent (person or algorithm).
# TODO: Keep track of edit history, e.g. bounds adjustments?
#
# TODO: Should we try to help ensure that the start index and start
# time are consistent, or just leave that up to code that constructs
# and modifies clips?
#
# TODO: Add uniqueness constraint to prevent creation of duplicate clips.
class Clip(Model):
    
    station = ForeignKey(
        Station, on_delete=CASCADE, related_name='clips')
    recorder = ForeignKey(
        Device, on_delete=CASCADE, related_name='clips')
    recording = ForeignKey(
        Recording, null=True, on_delete=SET_NULL, related_name='clips')
    channel_num = IntegerField(null=True)
    start_index = BigIntegerField(null=True)
    length = BigIntegerField()
    sample_rate = FloatField()
    start_time = DateTimeField()
    end_time = DateTimeField()
    creation_time = DateTimeField(null=True)
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='clips')
    creating_job = ForeignKey(
        Job, null=True, on_delete=CASCADE, related_name='clips')
    imported_file_path = CharField(max_length=255, null=True) # long enough?
    file_path = CharField(max_length=255, unique=True, null=True) # long enough?
    
    def __str__(self):
        return 'Clip {} {} {} {} {} "{}"'.format(
            str(self.recording), self.channel_num, self.start_index,
            self.length, self.start_time, self.file_path)
        
    class Meta:
        db_table = 'vesper_clip'
        
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
    return os.path.join(settings.VESPER_DATA_DIR, 'Clips', *path_parts)


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
    
    
# This is an old `Clip` model that did not allow `None` values for the
# `recording` or `channel_num` fields, and that did not include `station`
# and `recording` fields.
# class Clip(Model):
#     recording = ForeignKey(Recording, on_delete=CASCADE, related_name='clips')
#     channel_num = IntegerField()
#     start_index = BigIntegerField(null=True)
#     length = BigIntegerField()
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     file_path = CharField(max_length=255, unique=True, null=True) # Long enough?
#     def __str__(self):
#         return 'Clip {} {} {} {} {} "{}"'.format(
#             str(self.recording), self.channel_num, self.start_index,
#             self.length, self.start_time, self.file_path)
#     class Meta:
#         db_table = 'vesper_clip'
    
    
# This is an old model devoted specifically to clips without parent
# recordings. It is subsumed by the most recent `Clip` model.
# class OrphanedClip(Model):
#     station = ForeignKey(
#         Station, on_delete=CASCADE, related_name='orphaned_clips')
#     recorder = ForeignKey(
#         Device, on_delete=CASCADE, related_name='orphaned_clips')
#     channel_num = IntegerField()
#     length = BigIntegerField()
#     sample_rate = FloatField()
#     start_time = DateTimeField()
#     end_time = DateTimeField()
#     class Meta:
#         db_table = 'vesper_orphaned_clips'


# For common annotations this table allows you to associate a description
# with the annotation name.
class AnnotationInfo(Model):
    name = CharField(max_length=255, unique=True) # e.g. 'Classification'
    description = TextField(blank=True)
    class Meta:
        db_table = 'vesper_annotation_info'
    
    
# TODO: Automatically track annotation creator and edit history.
class Annotation(Model):
    clip = ForeignKey(Clip, on_delete=CASCADE, related_name='annotations')
    name = CharField(max_length=255)      # e.g. 'Classification', 'Outside'
    value = TextField(blank=True)         # e.g. 'NFC.AMRE', 'True'
    creation_time = DateTimeField(null=True)
    creating_user = ForeignKey(
        User, null=True, on_delete=CASCADE, related_name='annotations')
    creating_job = ForeignKey(
        Job, null=True, on_delete=CASCADE, related_name='annotations')
    class Meta:
        unique_together = ('clip', 'name')
        db_table = 'vesper_annotation'
