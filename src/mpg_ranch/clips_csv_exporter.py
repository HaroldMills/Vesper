"""Module containing class `ClipsCsvExporter`."""


from __future__ import print_function

import datetime
import os.path

from six import string_types
import yaml

from vesper.util.bunch import Bunch
from vesper.vcl.clip_visitor import ClipVisitor
from vesper.vcl.command import CommandExecutionError
import vesper.util.os_utils as os_utils
import vesper.vcl.vcl_utils as vcl_utils


# TODO: Allow specification of table format YAML file via command line.
_TABLE_FORMAT = yaml.load('''

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
      
''')

     
# TODO: Write file in chunks to avoid accumulating an unreasonable
# number of table lines in memory.


class ClipsCsvExporter(ClipVisitor):
    
    
    def __init__(self, positional_args, keyword_args):
        super(ClipsCsvExporter, self).__init__(positional_args, keyword_args)
        (self._output_file_path,) = \
            vcl_utils.get_required_keyword_arg('output-file', keyword_args)
        self._columns = _create_table_columns(_TABLE_FORMAT)
        
        
    export = ClipVisitor.visit_clips
        
        
    def begin_visits(self):
        column_names = [c.name for c in self._columns]
        self._lines = [','.join(column_names)]
        
        
    def visit(self, clip):
        values = [_get_column_value(c, clip) for c in self._columns]
        self._lines.append(','.join(values))
        
        
    def end_visits(self):
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
    
    if isinstance(measurement, string_types):
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
        
    elif isinstance(format_, string_types):
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


class ClipClassMeasurement(object):
    
    name = 'Clip Class'
    
    def measure(self, clip):
        return clip.clip_class_name
    
    
class DetectorMeasurement(object):
    
    name = 'Detector'
    
    def measure(self, clip):
        return clip.detector_name
    
    
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
        
        class_name = clip.clip_class_name
        
        if not class_name.startswith('Call.'):
            return False
        
        else:
            # clip is a call
            
            if class_name in self._ignored_class_names:
                return False
            
            else:
                # call class should not be ignored
                
                key = (clip.station.name, clip.detector_name, class_name)
                last_time = self._last_call_times.get(key)
                
                time = clip.start_time
                self._last_call_times[key] = time
                
                if last_time is None:
                    # first call of this class
                    
                    return False
                
                else:
                    # not first call of this class
                    
                    return time - last_time < self._min_intercall_interval
    
    
class ElapsedStartTimeMeasurement(object):
    
    name = 'Elapsed Start Time'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is not None:
            return clip.start_time - recording.start_time
        else:
            return None
        
            
class EmptyMeasurement(object):
    
    name = 'Empty'
    
    def measure(self, clip):
        return ''
    
    
class FileNameMeasurement(object):
    
    name = 'File Name'
    
    def measure(self, clip):
        return os.path.basename(clip.file_path)
    
    
class NightMeasurement(object):
    
    name = 'Night'
    
    def measure(self, clip):
        return clip.night
    
    
class RecordingDurationMeasurement(object):
    
    name = 'Recording Duration'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is not None:
            return recording.duration
        else:
            return None
        
        
class RecordingStartTimeMeasurement(object):
    
    name = 'Recording Start Time'
    
    def measure(self, clip):
        recording = clip.recording
        if recording is not None:
            time_zone = recording.station.time_zone
            return recording.start_time.astimezone(time_zone)
        else:
            return None
    
    
# TODO: Implement more general time rounding in `time_utils`.


class RoundedStartTimeMeasurement(object):
    
    
    name = 'Rounded Start Time'
    
    
    def measure(self, clip):
        
        time_zone = clip.station.time_zone
        time = clip.start_time.astimezone(time_zone)
        seconds_after_the_hour = time.minute * 60 + time.second
        
        time = time.replace(minute=0, second=0, microsecond=0)
        
        half_hours = int(round(seconds_after_the_hour / 1800.))
        delta = datetime.timedelta(seconds=half_hours * 1800)
        
        return time + delta
    
    
class StartTimeMeasurement(object):
    
    name = 'Start Time'
    
    def measure(self, clip):
        time_zone = clip.station.time_zone
        return clip.start_time.astimezone(time_zone)
    
    
class StationMeasurement(object):
    
    name = 'Station'
    
    def measure(self, clip):
        return clip.station.name
    
    
_MEASUREMENT_CLASSES = dict((c.name, c) for c in [
    ClipClassMeasurement,
    DetectorMeasurement,
    DuplicateCallMeasurement,
    ElapsedStartTimeMeasurement,
    EmptyMeasurement,
    FileNameMeasurement,
    NightMeasurement,
    RecordingDurationMeasurement,
    RecordingStartTimeMeasurement,
    RoundedStartTimeMeasurement,
    StartTimeMeasurement,
    StationMeasurement
])


class BirdMigrationSeasonFormat(object):
    
    name = 'Bird Migration Season'
        
    def format(self, date):
        return 'Fall' if date.month >= 7 else 'Spring'
    
    
class BooleanFormat(object):
    
    name = 'Boolean'
    
    def __init__(self, parameters=None):
        if parameters is None:
            parameters = {}
        self._values = parameters.get('values', {True: 'True', False: 'False'})
        
    def format(self, value):
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
        if clip_class_name.startswith(prefix):
            name = clip_class_name[len(prefix):]
            return self._mapping.get(name, name.lower())
        else:
            return ''
        
           
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
        return value.lower()
    
    
class MappingFormat(object):
    
    name = 'Mapping'
    
    def __init__(self, parameters=None):
        if parameters is None:
            self._mapping = {}
        else:
            self._mapping = parameters.get('mapping', {})
            
    def format(self, value):
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
        time = time.strftime(self._format)
        if self._quote:
            return '"' + time + '"'
        else:
            return time
    
    
_FORMAT_CLASSES = dict((c.name, c) for c in [
    BirdMigrationSeasonFormat,
    BooleanFormat,
    CallClipClassFormat,
    DurationFormat,
    LowerCaseFormat,
    MappingFormat,
    TimeFormat
])
