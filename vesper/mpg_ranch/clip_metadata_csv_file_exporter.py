"""Module containing class `ClipMetadataCsvFileExporter`."""


import datetime
import os.path

import pytz

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import AnnotationInfo, StringAnnotation
from vesper.ephem.astronomical_calculator import AstronomicalCalculatorCache
from vesper.singletons import clip_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.os_utils as os_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Change "Sun" and "Moon" to "Solar" and "Lunar" where appropriate.
# TODO: Change `klass` to `cls`.
# TODO: Change `(object)` to ``.
# TODO: Refactor solar event measurement classes to simplify them?

# TODO: Return UTC times instead of local times from all measurements
# (and from all astronomical calculators).

# TODO: Add clip as argument to formatters and offer two time formatters,
# "UTC Time" and "Local Time".

# TODO: Write file in chunks to avoid accumulating an unreasonable
# number of table lines in memory.

# TODO: Create a format superclass that provides a boolean `quote-values`
# option. (Or perhaps there should be a third option to quote only if
# needed.

# TODO: Provide exporter-level control of CSV options, like the
# separator and quote characters, the `None` value string, and whether
# or not values are quoted by default. Provide a function to escape
# quotes as needed.


# TODO: Allow specification of table format YAML file via command line.
_TABLE_FORMAT = yaml_utils.load('''

columns:

    - name: season
      measurement: Night
      format: Bird Migration Season
  
    - name: year
      measurement: Night
      format:
          name: Time
          parameters:
              format: "%Y"

    - name: detector
      measurement: Detector
      format: Lower Case

    - name: species
      measurement: Clip Class
      format:
          name: Call Clip Class
          parameters:
              mapping:
                  DoubleUp: dbup
                  Other: othe
                  Unknown: unkn
      
    - name: site
      measurement: Station
      format:
          name: Mapping
          parameters:
              mapping:
                  Baldy: baldy
                  Floodplain: flood
                  Ridge: ridge
                  Sheep Camp: sheep
      
    - name: date
      measurement: Night
      format:
          name: Time
          parameters:
              format: "%m/%d/%y"
              
    - name: recording_start
      measurement: Recording Start Time
      format: Time
              
    - name: recording_length
      measurement: Recording Duration
      format: Duration
              
    - name: detection_time
      measurement: Elapsed Start Time
      format: Duration
      
    - name: real_detection_time
      measurement: Start Time
      format:
          name: Time
          parameters:
              format: "%H:%M:%S"
              
    - name: real_detection_time
      measurement: Start Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
              
    - name: rounded_to_half_hour
      measurement: Rounded Start Time
      format: Time
      
    - name: duplicate
      measurement:
          name: Duplicate Call
          parameters:
              min_intercall_interval: 60
              ignored_classes: [Other, Unknown, Weak]
      format:
          name: Boolean
          parameters:
              values:
                  true: 'yes'
                  false: 'no'
                  
    - name: sunset
      measurement: Sunset Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dusk
      measurement: Civil Dusk Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dusk
      measurement: Nautical Dusk Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dusk
      measurement: Astronomical Dusk Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dawn
      measurement: Astronomical Dawn Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dawn
      measurement: Nautical Dawn Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dawn
      measurement: Civil Dawn Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: sunrise
      measurement: Sunrise Time
      format:
          name: Time
          parameters:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: moon_altitude
      measurement: Moon Altitude
      format:
          name: Decimal
          parameters:
              detail: ".1"

    - name: moon_illumination
      measurement: Moon Illumination
      format:
          name: Percent
          parameters:
              detail: ".1"
      
''')

     
# _TABLE_FORMAT = yaml_utils.load('''
#  
# columns:
#  
#     - name: Station
#       measurement: Station
#       format:
#           name: Mapping
#           parameters:
#               mapping:
#                   Floodplain: Floodplain NFC
#                   Sheep Camp: Sheep Camp NFC
#                   Ridge: Ridge NFC
#                   Baldy: Baldy NFC
#        
#     - name: Detector
#       measurement: Detector
#  
#     - name: Year
#       measurement: Night
#       format:
#           name: Time
#           parameters:
#               format: "%Y"
#  
#     - name: Season
#       measurement: Night
#       format: Bird Migration Season
#    
#     - name: Night
#       measurement: Night
#       format:
#           name: Time
#           parameters:
#               format: "%Y-%m-%d"
#  
#     - name: Start Date/Time (MDT)
#       measurement: Start Time
#       format:
#           name: Time
#           parameters:
#               format: "%Y-%m-%d %H:%M:%S"
#                
#     - name: Clip Class
#       measurement: Clip Class
#             
# ''')


_ASTRONOMICAL_CALCULATORS = \
    AstronomicalCalculatorCache(result_times_local=True)


class ClipMetadataCsvFileExporter(object):
    
    
    extension_name = 'Clip Metadata CSV File Exporter'
    
    
    def __init__(self, args):
        get = command_utils.get_required_arg
        self._output_file_path = get('output_file_path', args)
        self._columns = _create_table_columns(_TABLE_FORMAT)
    
    
    def begin_exports(self):
        column_names = [c.name for c in self._columns]
        self._lines = [','.join(column_names)]
    
    
    def export(self, clip):
        values = [_get_column_value(c, clip) for c in self._columns]
        self._lines.append(','.join(values))
        return True
        
        
    def end_exports(self):
        table = '\n'.join(self._lines) + '\n'
        try:
            os_utils.write_file(self._output_file_path, table)
        except OSError as e:
            raise CommandExecutionError(str(e))
        
        
def _create_table_columns(table_format):
    columns = table_format['columns']
    return [_create_table_column(c) for c in columns]


def _create_table_column(column):
    name = _get_column_name(column)
    measurement = _get_column_measurement(column)
    format_ = _get_column_format(column)
    return Bunch(name=name, measurement=measurement, format=format_)
    
    
def _get_column_name(column):
    return column['name']
    
    
def _get_column_measurement(column):
    
    # We assume that `column` has key `measurement`.
    measurement = column['measurement']
    
    if isinstance(measurement, str):
        # `measurement` is string measurement name
        
        klass = _MEASUREMENT_CLASSES[measurement]
        return klass()
    
    else:
        
        # We assume that `measurement` is a `dict`
        
        name = measurement['name']
        klass = _MEASUREMENT_CLASSES[name]
        parameters = measurement.get('parameters')
        if parameters is None:
            return klass()
        else:
            return klass(parameters)
    
    
def _get_column_format(column):
    
    format_ = column.get('format')
    
    if format_ is None:
        return None
        
    elif isinstance(format_, str):
        # `format_` is string format name
        
        klass = _FORMAT_CLASSES[format_]
        return klass()
        
    else:
        
        # We assume that `format_` is a `dict`.
        
        name = format_['name']
        klass = _FORMAT_CLASSES[name]
        parameters = format_.get('parameters')
        if parameters is None:
            return klass()
        else:
            return klass(parameters)
    
    
def _get_column_value(column, clip):
    
    value = column.measurement.measure(clip)
    
    format_ = column.format
    
    if format_ is None:
        return str(value)
    else:
        return format_.format(value)
    
    
def _create_measurements(table_format):
    columns = table_format['columns']
    return [_create_measurement(c) for c in columns]


def _create_measurement(column):
    name = column['measurement']
    klass = _MEASUREMENT_CLASSES[name]
    return klass()


class AstronomicalDawnMeasurement(object):
    
    name = 'Astronomical Dawn Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Astronomical Dawn')


def _get_time(clip, event_name):
    station = clip.station
    calculator = _ASTRONOMICAL_CALCULATORS.get_calculator(station)
    night = station.get_night(clip.start_time)
    return calculator.get_night_solar_event_time(night, event_name)
    
    
def _get_time_zone(name):
    return pytz.timezone(name)


class AstronomicalDuskMeasurement(object):
    
    name = 'Astronomical Dusk Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Astronomical Dusk')


class CivilDawnMeasurement(object):
    
    name = 'Civil Dawn Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Civil Dawn')


class CivilDuskMeasurement(object):
    
    name = 'Civil Dusk Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Civil Dusk')


class ClipClassMeasurement(object):
    
    name = 'Clip Class'
    
    def measure(self, clip):
        return _get_classification(clip)
    
    
_classification_annotation_info = None


def _get_classification_annotation_info():
    
    global _classification_annotation_info
    
    if _classification_annotation_info is None:
        _classification_annotation_info = \
            AnnotationInfo.objects.get(name='Classification')
            
    return _classification_annotation_info


def _get_classification(clip):
    
    try:
        annotation = StringAnnotation.objects.get(
            clip=clip, info=_get_classification_annotation_info())
        
    except StringAnnotation.DoesNotExist:
        return None
    
    else:
        return annotation.value
    
    
class DetectorMeasurement(object):
    
    name = 'Detector'
    
    def measure(self, clip):
        return model_utils.get_clip_type(clip)
    
    
class DuplicateCallMeasurement(object):
    
    
    # This measurement assumes that clips of a given clip class are
    # visited in order of increasing start time.
    
    
    name = 'Duplicate Call'
    
    
    def __init__(self, parameters=None):
        
        if parameters is None:
            parameters = {}
            
        interval = parameters.get('min_intercall_interval', 60)
        self._min_intercall_interval = datetime.timedelta(seconds=interval)
        
        names = parameters.get('ignored_classes', [])
        self._ignored_class_names = frozenset('Call.' + n for n in names)
        
        self._last_call_times = {}
        
    
    def measure(self, clip):
        
        class_name = _get_classification(clip)
        
        if class_name is None or not class_name.startswith('Call.'):
            return None
        
        else:
            # clip is a call
            
            if class_name in self._ignored_class_names:
                return None
            
            else:
                # call class should not be ignored
                
                detector_name = _get_detector_name(clip)
                key = (clip.station.name, detector_name, class_name)
                last_time = self._last_call_times.get(key)
                
                time = clip.start_time
                self._last_call_times[key] = time
                
                if last_time is None:
                    # first call of this class
                    
                    return False
                
                else:
                    # not first call of this class
                    
                    return time - last_time < self._min_intercall_interval
    
    
def _get_detector_name(clip):
    
    processor = clip.creating_processor
    
    if processor is None:
        return None
    
    else:
        return processor.name


class ElapsedStartTimeMeasurement(object):
    
    name = 'Elapsed Start Time'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is None:
            return None
        else:
            return clip.start_time - recording.start_time
        
            
class FileNameMeasurement(object):
    
    name = 'File Name'
    
    def measure(self, clip):
        audio_file_path = clip_manager.instance.get_audio_file_path(clip)
        if audio_file_path is None:
            return None
        else:
            return os.path.basename(audio_file_path)
    
    
class MoonAltitudeMeasurement(object):
    
    name = 'Moon Altitude'
    
    def measure(self, clip):
        return _get_lunar_position(clip).altitude
    
    
def _get_lunar_position(clip):
    calculator = _ASTRONOMICAL_CALCULATORS.get_calculator(clip.station)
    return calculator.get_lunar_position(clip.start_time)
    
    
class MoonAzimuthMeasurement(object):
    
    name = 'Moon Azimuth'
    
    def measure(self, clip):
        return _get_lunar_position(clip).azimuth
    
    
class MoonIlluminationMeasurement(object):
    
    name = 'Moon Illumination'
    
    def measure(self, clip):
        calculator = _ASTRONOMICAL_CALCULATORS.get_calculator(clip.station)
        return calculator.get_lunar_illumination(clip.start_time)
    
    
class NauticalDawnMeasurement(object):
    
    name = 'Nautical Dawn Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Nautical Dawn')


class NauticalDuskMeasurement(object):
    
    name = 'Nautical Dusk Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Nautical Dusk')


class NightMeasurement(object):
    
    name = 'Night'
    
    def measure(self, clip):
        return clip.date
    
    
class RecordingDurationMeasurement(object):
    
    name = 'Recording Duration'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is None:
            return None
        else:
            return datetime.timedelta(seconds=recording.duration)
        
        
class RecordingStartTimeMeasurement(object):
    
    name = 'Recording Start Time'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is None:
            return None
        else:
            time_zone = _get_time_zone(recording.station.time_zone)
            return recording.start_time.astimezone(time_zone)
    
    
# TODO: Use time rounding function of `time_utils`?
class RoundedStartTimeMeasurement(object):
    
    
    name = 'Rounded Start Time'
    
    
    def measure(self, clip):
        
        time_zone = _get_time_zone(clip.station.time_zone)
        time = clip.start_time.astimezone(time_zone)
        seconds_after_the_hour = time.minute * 60 + time.second
        
        time = time.replace(minute=0, second=0, microsecond=0)
        
        half_hours = int(round(seconds_after_the_hour / 1800.))
        delta = datetime.timedelta(seconds=half_hours * 1800)
        
        return time + delta
    
    
class StartTimeMeasurement(object):
    
    name = 'Start Time'
    
    def measure(self, clip):
        time_zone = _get_time_zone(clip.station.time_zone)
        return clip.start_time.astimezone(time_zone)
    
    
class StationMeasurement(object):
    
    name = 'Station'
    
    def measure(self, clip):
        return clip.station.name
    
    
class SunAltitudeMeasurement(object):
    
    name = 'Sun Altitude'
    
    def measure(self, clip):
        return _get_solar_position(clip).altitude
    
    
def _get_solar_position(clip):
    calculator = _ASTRONOMICAL_CALCULATORS.get_calculator(clip.station)
    return calculator.get_solar_position(clip.start_time)
    
    
class SunAzimuthMeasurement(object):
    
    name = 'Sun Azimuth'
    
    def measure(self, clip):
        return _get_solar_position(clip).azimuth
    
    
class SunriseTimeMeasurement(object):
    
    name = 'Sunrise Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Sunrise')
    
    
class SunsetTimeMeasurement(object):
    
    name = 'Sunset Time'
    
    def measure(self, clip):
        return _get_time(clip, 'Sunset')
    
    
_MEASUREMENT_CLASSES = dict((c.name, c) for c in [
    AstronomicalDawnMeasurement,
    AstronomicalDuskMeasurement,
    CivilDawnMeasurement,
    CivilDuskMeasurement,
    ClipClassMeasurement,
    DetectorMeasurement,
    DuplicateCallMeasurement,
    ElapsedStartTimeMeasurement,
    FileNameMeasurement,
    MoonAltitudeMeasurement,
    MoonAzimuthMeasurement,
    MoonIlluminationMeasurement,
    NauticalDawnMeasurement,
    NauticalDuskMeasurement,
    NightMeasurement,
    RecordingDurationMeasurement,
    RecordingStartTimeMeasurement,
    RoundedStartTimeMeasurement,
    StartTimeMeasurement,
    StationMeasurement,
    SunAltitudeMeasurement,
    SunAzimuthMeasurement,
    SunriseTimeMeasurement,
    SunsetTimeMeasurement
])


_NONE_STRING = ''


class BirdMigrationSeasonFormat(object):
    
    name = 'Bird Migration Season'
        
    def format(self, date):
        if date is None:
            return _NONE_STRING
        else:
            return 'Fall' if date.month >= 7 else 'Spring'
    
    
_DEFAULT_BOOLEAN_VALUES = {
    True: 'True',
    False: 'False'
}


class BooleanFormat(object):
    
    name = 'Boolean'
    
    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        self._values = parameters.get('values', _DEFAULT_BOOLEAN_VALUES)
        
    def format(self, value):
        if value is None:
            return _NONE_STRING
        else:
            return self._values[value]
    
    
class CallClipClassFormat(object):
    
    name = 'Call Clip Class'
    
    def __init__(self, parameters=None):
        if parameters is None:
            self._mapping = {}
        else:
            self._mapping = parameters.get('mapping', {})
            
    def format(self, clip_class_name):
        prefix = 'Call.'
        if clip_class_name is None or not clip_class_name.startswith(prefix):
            return _NONE_STRING
        else:
            name = clip_class_name[len(prefix):]
            return self._mapping.get(name, name.lower())
        
           
class DecimalFormat(object):
    
    name = 'Decimal'
    
    def __init__(self, parameters=None):
        if parameters is None:
            self._format = '{:f}'
        else:
            self._format = '{:' + parameters.get('detail', '') + 'f}'
            
    def format(self, x):
        return self._format.format(x)


class PercentFormat(DecimalFormat):
    
    name = 'Percent'
    
    def format(self, x):
        return self._format.format(100 * x)


class DurationFormat(object):

    
    name = 'Duration'
    
    
    def __init__(self, parameters=None):
        
        if parameters is None:
            self._format = '{:d}:{:02d}:{:02d}'
            self._quote = False
            
        else:
            
            sep = parameters.get('separator', ':')
            num_hours_digits = parameters.get('num_hours_digits')
            
            if num_hours_digits is None:
                hours_format = '{:d}'
            else:
                hours_format = '{:0' + str(num_hours_digits) + '}'
                
            self._format = hours_format + sep + '{:02d}' + sep + '{:02d}'
            self._quote = parameters.get('quote', False)
        
        
    def format(self, duration):
        
        if duration is None:
            return _NONE_STRING
        
        else:
            
            seconds = duration.total_seconds()
            
            hours = int(seconds // 3600)
            seconds -= hours * 3600
            
            minutes = int(seconds // 60)
            seconds -= minutes * 60
            
            seconds = int(round(seconds))
            
            duration = self._format.format(hours, minutes, seconds)
            
            if self._quote:
                return '"' + duration + '"'
            else:
                return duration

    
class LowerCaseFormat(object):
    
    name = 'Lower Case'
    
    def format(self, value):
        if value is None:
            return _NONE_STRING
        else:
            return value.lower()
    
    
class MappingFormat(object):
    
    name = 'Mapping'
    
    def __init__(self, parameters=None):
        if parameters is None:
            self._mapping = {}
        else:
            self._mapping = parameters.get('mapping', {})
            
    def format(self, value):
        if value is None:
            return _NONE_STRING
        else:
            return self._mapping.get(value, value)
    
    
class TimeFormat(object):
    
    name = 'Time'
    
    # TODO: Validate format by creating a date and invoking strftime
    # on the format. What exceptions can this raise and how do we
    # handle them?
    
    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        self._format = parameters.get('format', '%H:%M:%S')
        self._quote = parameters.get('quote', False)
        
        
    def format(self, time):
        if time is None:
            return _NONE_STRING
        else:
            time = time.strftime(self._format)
            if self._quote:
                return '"' + time + '"'
            else:
                return time
    
    
_FORMAT_CLASSES = dict((c.name, c) for c in [
    BirdMigrationSeasonFormat,
    BooleanFormat,
    CallClipClassFormat,
    DecimalFormat,
    PercentFormat,
    DurationFormat,
    LowerCaseFormat,
    MappingFormat,
    TimeFormat
])
