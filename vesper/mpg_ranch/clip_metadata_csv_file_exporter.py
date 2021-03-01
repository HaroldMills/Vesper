"""Module containing class `ClipMetadataCsvFileExporter`."""


from datetime import datetime as DateTime, timedelta as TimeDelta
from pathlib import Path
import csv
import tempfile

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import AnnotationInfo
from vesper.ephem.sun_moon import SunMoon, SunMoonCache
from vesper.util.bunch import Bunch
from vesper.util.datetime_formatter import DateTimeFormatter
from vesper.util.time_difference_formatter import (
    TimeDifferenceFormatter as TimeDifferenceFormatter_)
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils


'''
A *measurement* produces a value from a clip.
A *format* transforms a value for display.
'''


'''
Recent Clip Count measurement settings:
    count_interval_size (seconds, default 3600)
    included_classifications - list, default [*]
    excluded_classifications - list, default []
    lumped_classifications - list of lists, default []

Expression Evaluator operators:

    null
    true
    false
    <number>
    x
    
    add
    sub
    mul
    div
    idiv
    mod
    
    pow
    exp
    ln
    log10
    
    abs
    neg
    ceiling
    floor
    round
    truncate
    
    int
    float
    
    gt
    ge
    lt
    le
    eq
    ne
    
    not
    and
    or
    xor


columns:

    - name: Time Before Sunrise
      measurement:
          name: Relative Start Time
          settings: {reference_time: Sunrise, negate: true}
      formatter: Time Difference Formatter


Formatter classes:
    +ExpressionEvaluator (Number -> Number)
    -BooleanFormatter, (Boolean -> String)
    CallSpeciesFormatter, (String -> String)
    DecimalFormatter, (Number -> String)
    LocalTimeFormatter, (DateTime -> String)
    LowerCaseFormatter, (String -> String)
    ValueMapper, (Any -> Any)
    -NocturnalBirdMigrationSeasonFormatter, (DateTime -> String)
    PercentFormatter, (Number -> String)
    TimeDifferenceFormatter, (Number -> String)
    +UpperCaseFormatter, (String -> String)
    UtcTimeFormatter, (DateTime -> String)
    
All formatters but `ValueMapper` automatically map `None` to `None`,
and this behavior cannot be modified.

By default, `ValueMapper` maps keys for which values are not specified
to themselves, so it maps `None` to `None`. A different value for `None`
can be specified explicitly just as for any other key.

`ValueMapper` has a `default` setting that allows specification of a
default mapping value. When this setting is present, keys for which
values are not specified in the `mapping` setting are mapped to the
default.
'''


# TODO: Eliminate `BooleanFormatter`.

# TODO: Add `ExpressionEvaluator`.

# Reimplement some column formatters using new classes, eliminating
# `NocturnalBirdMigrationSeasonFormatter`.

# TODO: Generalize `CallSpeciesFormatter` to strip prefix if present
# and otherwise return empty string? Maybe `SubclassificationFormatter`?

# TODO: Add "Recent Clip Count" measurement. Reimplement "duplicate"
# column in terms of it.

# TODO: Add `UpperCaseFormatter`.

# TODO: Implement table format presets.

# TODO: Make each archive either day-oriented or night-oriented, with
# orientation specified in "Archive Settings.yaml". Make `day` setting
# optional for solar event measurements and use day/night orientation
# to determine default value.

# TODO: Use `jsonschema` package to check table format specification.

# TODO: Support default format specification in measurement classes.

# TODO: Consider supporting user-defined formats. These would appear in
# a YAML `formats` associated array that accompanies the `columns` array.
# The `formats` array would map user-defined format names to format
# specifications.

# TODO: Consider supporting user-defined default value formats. These
# would appear in a YAML `default_formats` associative array that
# accompanies the `columns` array. The `default_formats` array would
# map column value type names to format specifications. Vesper would
# define a limited number of value types, e.g. String, Integer, Float,
# and DateTime. Would measurements be able to define their own types?
# Maybe not initially, at least.

# TODO: Consider moving measurement and format settings up one level
# in specification dictionaries, i.e. eliminating "settings"  key.
# The disadvantage of this is the possibility of collisions between
# setting names and specification item keys. Currently, though, the
# only specification keys we use are "name" and "settings".


'''
Measurements by name:

    Annotation Value
    Astronomical Dawn
    Astronomical Dusk
    Civil Dawn
    Civil Dusk
    Detector Name
    Detector Type
    Duration
    End Time
    File Name
    Lunar Altitude
    Lunar Azimuth
    Lunar Illumination
    Microphone Output Name
    Nautical Dawn
    Nautical Dusk
    Possible Repeated Call
    Recording Duration
    Recording End Time
    Recording Length
    Recording Start Time
    Relative Start Time
    Solar Altitude
    Solar Azimuth
    Solar Midnight
    Solar Noon
    Solar Period
    Start Time
    Station Name
    Sunrise
    Sunset
'''


'''
Measurements by category, with some additions:

Recording:
    Recording Start Time
    Recording End Time
    Recording Duration
    Recording Length
    Recording Channel Number

Clip:
    ID
    Station Name
    Microphone Output Name
    Detector Name
    Detector Type

Time:
    Start Time
    End Time
    Relative Start Time
    Relative End Time
    Duration
    Start Index
    End Index
    Length
    Sample Rate

Annotations:
    Annotation Value

Calling:
    + Calling Rate
    Possible Repeated Call

Sun:
    Astronomical Dawn
    Astronomical Dusk
    Civil Dawn
    Civil Dusk
    Nautical Dawn
    Nautical Dusk
    Solar Altitude
    Solar Azimuth
    Solar Midnight
    Solar Noon
    Solar Period
    Sunrise
    Sunset

Moon:
    Lunar Altitude
    Lunar Azimuth
    Lunar Illumination
'''


"""
_TABLE_FORMAT_NEW = yaml_utils.load('''

columns:

    - name: Migration Season
      measurement: Start Time
      formatter:
          - name: Local Time Formatter
            settings: {format: "%m"}
          - name: Expression Evaluator
            settings: {expression: "x int 6 gt"}
          - name: Value Mapper
            settings: {mapping: {false: Spring, true: Fall}}
  
    - name: year
      measurement: Start Time
      formatter:
          - name: Solar Date Finder
            settings: {day: false}
          - name: Date Formatter
            settings: {format: "%Y"}

    - name: detector
      measurement: Detector Type
      formatter: Lower Case Formatter

    - name: species
      measurement:
          name: Annotation Value
          settings: {annotation_name: Classification}
      formatter:
          - Call Species Formatter
          - name: Value Mapper
            settings:
                mapping:
                    DoubleUp: dbup
                    Other: othe
                    Unknown: unkn
          - Lower Case Formatter
      
    - name: site
      measurement: Station Name
      formatter:
          name: Value Mapper
          settings:
              mapping:
                  Baldy: baldy
                  Floodplain: flood
                  Ridge: ridge
                  Sheep Camp: sheep
      
    - name: date
      measurement: Start Time
      formatter:
          - name: Solar Date Finder
            settings: {day: False}
          - name: Date Formatter
            settings: {format: "%m/%d/%y"}
              
    - name: recording_start
      measurement: Recording Start Time
      formatter:
          - name: Local Time Formatter
            settings: {format: "%H:%M:%S"}
      
    - name: recording_length
      measurement: Recording Duration
      formatter: Time Difference Formatter
              
    - name: detection_time
      measurement: Relative Start Time
      formatter: Time Difference Formatter
      
    - name: real_detection_time
      measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings: {format: "%H:%M:%S"}
              
    - name: real_detection_time
      measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
              
    - name: rounded_to_half_hour
      measurement: Start Time
      formatter:
          - name: Time Rounder
            settings: {increment: 1800}
          - name: Local Time Formatter
            settings: {format: "%H:%M:%S"}
      
    - name: duplicate
      measurement:
          name: Recent Call Count
          settings:
              count_interval_size: 60
              excluded_classifications: [Other, Unknown, Weak]
      formatter:
          - name: Expression Evaluator
            settings: {expression: "x 1 gt"}
          - name: Value Mapper
            settings: {false: "no", true: "yes"}
    
    - name: sunset
      measurement:
          name: Sunset
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: civil_dusk
      measurement:
          name: Civil Dusk
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: nautical_dusk
      measurement:
          name: Nautical Dusk
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: astronomical_dusk
      measurement:
          name: Astronomical Dusk
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: astronomical_dawn
      measurement:
          name: Astronomical Dawn
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: nautical_dawn
      measurement:
          name: Nautical Dawn
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: civil_dawn
      measurement:
          name: Civil Dawn
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: sunrise
      measurement:
          name: Sunrise
          settings: {day: false}
      formatter:
          name: Local Time Formatter
          settings: {format: "%m/%d/%y %H:%M:%S"}
      
    - name: moon_altitude
      measurement: Lunar Altitude
      formatter:
          name: Decimal Formatter
          settings: {detail: ".1"}

    - name: moon_illumination
      measurement: Lunar Illumination
      formatter:
          name: Percent Formatter
          settings: {detail: ".1"}
''')
"""


_TABLE_FORMAT = yaml_utils.load('''

columns:

    - name: season
      measurement: Start Time
      formatter: Nocturnal Bird Migration Season Formatter
  
    - name: year
      measurement: Start Time
      formatter:
          name: Solar Date Formatter
          settings:
              day: False
              format: "%Y"

    - name: detector
      measurement: Detector Type
      formatter: Lower Case Formatter

    - name: species
      measurement:
          name: Annotation Value
          settings:
              annotation_name: Classification
      formatter:
          - Call Species Formatter
          - name: Value Mapper
            settings:
                mapping:
                    DoubleUp: dbup
                    Other: othe
                    Unknown: unkn
          - Lower Case Formatter
      
    - name: site
      measurement: Station Name
      formatter:
          name: Value Mapper
          settings:
              mapping:
                  Baldy: baldy
                  Floodplain: flood
                  Ridge: ridge
                  Sheep Camp: sheep
      
    - name: date
      measurement: Start Time
      formatter:
          name: Solar Date Formatter
          settings:
              day: False
              format: "%m/%d/%y"
              
    - name: recording_start
      measurement: Recording Start Time
      formatter:
          name: Local Time Formatter
          settings:
              format: "%H:%M:%S"
      
    - name: recording_length
      measurement: Recording Duration
      formatter: Time Difference Formatter
              
    - name: detection_time
      measurement: Relative Start Time
      formatter: Time Difference Formatter
      
    - name: real_detection_time
      measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings:
              format: "%H:%M:%S"
              
    - name: real_detection_time
      measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
              
    - name: rounded_to_half_hour
      measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings:
              format: "%H:%M:%S"
              rounding_increment: 1800
      
    - name: duplicate
      measurement:
          name: Possible Repeated Call
          settings:
              min_intercall_interval: 60
              ignored_classifications: [Other, Unknown, Weak]
      formatter:
          - Boolean Formatter
          - name: Value Mapper
            settings:
                mapping:
                    'True': 'yes'
                    'False': 'no'
    
    - name: sunset
      measurement:
          name: Sunset
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dusk
      measurement:
          name: Civil Dusk
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dusk
      measurement:
          name: Nautical Dusk
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dusk
      measurement:
          name: Astronomical Dusk
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dawn
      measurement:
          name: Astronomical Dawn
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dawn
      measurement:
          name: Nautical Dawn
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dawn
      measurement:
          name: Civil Dawn
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: sunrise
      measurement:
          name: Sunrise
          settings:
              day: False
      formatter:
          name: Local Time Formatter
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: moon_altitude
      measurement: Lunar Altitude
      formatter:
          name: Decimal Formatter
          settings:
              detail: ".1"

    - name: moon_illumination
      measurement: Lunar Illumination
      formatter:
          name: Percent Formatter
          settings:
              detail: ".1"
''')


#     - name: twilight
#       measurement: Solar Period
#       formatter:
#           name: Value Mapper
#           settings:
#               mapping:
#                   Day: day
#                   Evening Civil Twilight: civil_twilight
#                   Evening Nautical Twilight: nautical_twilight
#                   Evening Astronomical Twilight: astronomical_twilight
#                   Night: night
#                   Morning Astronomical Twilight: astronomical_twilight
#                   Morning Nautical Twilight: nautical_twilight
#                   Morning Civil Twilight: civil_twilight
#         
#     - name: dusk_dawn
#       measurement: Solar Period
#       formatter:
#           name: Value Mapper
#           settings:
#               mapping:
#                   Day: day
#                   Evening Civil Twilight: dusk
#                   Evening Nautical Twilight: dusk
#                   Evening Astronomical Twilight: dusk
#                   Night: night
#                   Morning Astronomical Twilight: dawn
#                   Morning Nautical Twilight: dawn
#                   Morning Civil Twilight: dawn
#         
# ''')


# _TABLE_FORMAT = yaml_utils.load('''
#   
# columns:
#  
#     - Recording Start Time
#     
#     - measurement: Recording End Time
#       format:
#           name: Local Time
#           settings:
#               format: "%Y-%m-%d %H:%M:%S.%3f"
#     
#     - Recording Duration
#     - Recording Length
#     - Recording Channel Number
#     - ID
#     
#     - measurement: Start Time
#       format:
#           name: Local Time
#           settings:
#               format: "%Y-%m-%d %H:%M:%S.%4f"
#     
#     - measurement: End Time
#       format:
#           name: UTC Time
#           settings:
#               format: "%Y-%m-%d %H:%M:%S.%3f"
# 
#     - Duration
#      
#     - measurement: Start Index
#      
#     - measurement:
#           name: End Index
#      
#     - name: Length
#      
#     - name: Sample Rate
#       format:
#           name: Decimal
#           settings:
#               detail: ".0"
#      
#     # Uncomment any one of the following to elicit an error:
#      
#     # no name or measurement
#     # - {}
#      
#     # unrecognized measurement name
#     # - Bobo
#      
#     # unrecognized format name
#     # - name: Sample Rate
#     #   format: Bobo
#      
#     # missing format name
#     # - name: Sample Rate
#     #   format: {}
#  
# ''')


'''
Example relative start time column specs:

    - name: Time Before Recording End
      measurement:
          name: Relative Start Time
          settings:
              reference_time: Recording End Time
              negate: true
      formatter: Time Difference Formatter
    
    - name: Time After Sunset
      measurement:
          name: Relative Start Time
          settings:
              reference_time: Sunset
              day: false
      format: Time Difference

    - name: Time Before Sunrise
      measurement:
          name: Relative Start Time
          settings:
              reference_time: Sunrise
              day: false
              negate: true
      format: Time Difference Formatter
'''


_SUN_MOONS = SunMoonCache()


class ClipMetadataCsvFileExporter:
    
    
    extension_name = 'Clip Metadata CSV File Exporter'
    
    _OUTPUT_CHUNK_SIZE = 100
    
    
    def __init__(self, args):
        get = command_utils.get_required_arg
        self._output_file_path = get('output_file_path', args)
        self._columns = _create_table_columns(_TABLE_FORMAT)
        self._rows = []
    
    
    def begin_exports(self):
        self._open_output_file()
        column_names = [c.name for c in self._columns]
        self._write_row(column_names)
    
    
    def _open_output_file(self):
        
        # Create output file in temporary file directory.
        try:
            self._output_file = tempfile.NamedTemporaryFile(
                'wt', prefix='vesper-', suffix='.csv', delete=False)
        except Exception as e:
            self._handle_output_error('Could not open output file.', e)
        
        # Create output CSV writer.
        try:
            self._output_writer = csv.writer(self._output_file)
        except Exception as e:
            self._handle_output_error(
                'Could not create output file CSV writer.', e)
    
    
    def _handle_output_error(self, message, e):
        raise CommandExecutionError(f'{message} Error message was: {str(e)}.')
    
    
    def _write_row(self, row):
        self._rows.append(row)
        if len(self._rows) == self._OUTPUT_CHUNK_SIZE:
            self._write_rows()
    
    
    def _write_rows(self):
        
        # Write output rows.
        try:
            self._output_writer.writerows(self._rows)
        except Exception as e:
            self._handle_output_error('Could not write to output file.', e)
        
        self._rows = []
    
    
    def export(self, clip):
        row = [_get_column_value(c, clip) for c in self._columns]
        self._write_row(row)
        return True
    
    
    def end_exports(self):
        
        if len(self._rows) != 0:
            self._write_rows()
            
        temp_file_path = Path(self._output_file.name)
        
        # Close output file.
        try:
            self._output_file.close()
        except Exception as e:
            self._handle_output_error('Could not close output file.', e)
        
        # Move output file from temporary file directory to specified
        # location.
        try:
            temp_file_path.rename(self._output_file_path)
        except Exception as e:
            self._handle_output_error('Could not rename output file.', e)
    
    
def _create_table_columns(table_format):
    
    try:
        columns = table_format['columns']
    except KeyError:
        raise CommandExecutionError(
            'Clip table format lacks required "columns" item.')
        
    return [_create_table_column(c, i + 1) for i, c in enumerate(columns)]


def _create_table_column(column, column_num):
    
    try:
        return _create_table_column_aux(column, column_num)
    except Exception as e:
        raise CommandExecutionError(
            f'Error parsing clip table format: {str(e)}')


def _create_table_column_aux(column, column_num):
    
    if isinstance(column, str):
        # `column` is string
        
        # `column` both column name and measurement name.
        
        name = column
        measurement = _get_measurement_from_name(name)
        formatter = None
    
    else:
        # `column` is not string
        
        # We assume that `column` is a `dict`.
        
        name, measurement = \
            _get_column_name_and_measurement(column, column_num)
        formatter = _get_column_formatter(column, name)
    
    return Bunch(name=name, measurement=measurement, formatter=formatter)


def _get_measurement_from_name(name):
    cls = _get_measurement_class(name)
    return cls()
    

def _get_measurement_class(name):
    try:
        return _MEASUREMENT_CLASSES[name]
    except KeyError:
        raise CommandExecutionError(
            f'Unrecognized measurement name "{name}".')


def _get_column_name_and_measurement(column, column_num):
    
    measurement = column.get('measurement')
    
    if measurement is None:
        # measurement not specified
        
        try:
            name = column['name']
        except KeyError:
            raise CommandExecutionError(
                f'Neither name nor measurement is specified for '
                f'column {column_num}. Either name or measurement must '
                f'be specified for every column.')
        
        measurement = _get_measurement_from_name(name)
    
    else:
        # measurement specified
        
        if isinstance(measurement, str):
            # `measurement` is string measurement name
            
            measurement = _get_measurement_from_name(measurement)
        
        else:
            
            # We assume that `measurement` is a `dict`
            
            name = _get_measurement_name(measurement, column_num)
            cls = _get_measurement_class(name)
            settings = measurement.get('settings')
            if settings is None:
                measurement = cls()
            else:
                measurement = cls(settings)
        
        name = column.get('name', measurement.name)
    
    return name, measurement


def _get_measurement_name(measurement, column_num):
    try:
        return measurement['name']
    except KeyError:
        raise CommandExecutionError(
            f'Measurement specification for column {column_num} is '
            f'missing required "name" item.')


def _get_column_formatter(column, name):
    
    try:
        
        formatter = column.get('formatter')
        
        if formatter is None:
            return None
        
        elif isinstance(formatter, (list, tuple)):
            # sequence of formatter specifications
            
            return [_get_formatter(f) for f in formatter]
        
        else:
            # single formatter specification
            
            return _get_formatter(formatter)
    
    except Exception as e:
        raise CommandExecutionError(f'For column "{name}": {str(e)}')


def _get_formatter(formatter):
    
    if isinstance(formatter, str):
        # string formatter name
        
        cls = _get_formatter_class(formatter)
        return cls()
        
    else:
        # `dict` formatter specification
        
        name = _get_formatter_name(formatter)
        cls = _get_formatter_class(name)
        settings = formatter.get('settings')
        if settings is None:
            return cls()
        else:
            return cls(settings)
    
    
def _get_formatter_class(name):
    try:
        return _FORMATTER_CLASSES[name]
    except KeyError:
        raise CommandExecutionError(
            f'Unrecognized formatter name "{name}".')


def _get_formatter_name(formatter):
    try:
        return formatter['name']
    except KeyError:
        raise CommandExecutionError(
            'Formatter specification is missing required "name" item.')


def _get_column_value(column, clip):
    
    value = column.measurement.measure(clip)
    
    formatter = column.formatter
    
    if formatter is None:
        return str(value)
    
    elif isinstance(formatter, (list, tuple)):
        # sequence of formatters
        
        for f in formatter:
            value = f.format(value, clip)
        return value
            
    else:
        # single formatter
        
        return formatter.format(value, clip)
    
    
class AnnotationValueMeasurement:
    
    name = 'Annotation Value'
    
    def __init__(self, settings):
        annotation_name = settings.get('annotation_name')
        if annotation_name is None:
            raise ValueError(
                'Measurement settings lack required "annotation_name" item.')
        self._annotation_info = \
            AnnotationInfo.objects.get(name=annotation_name)
    
    def measure(self, clip):
        return model_utils.get_clip_annotation_value(
            clip, self._annotation_info)
        

class _SolarEventTimeMeasurement:
    
    def __init__(self, settings):
        self._day = settings.get('day')
        if self._day is None:
            raise ValueError('Measurement settings lack required "day" item.')
        
    def measure(self, clip):
        return _get_solar_event_time(clip, self.name, self._day)


def _get_solar_event_time(clip, event_name, day):
    sun_moon = _get_sun_moon(clip)
    date = sun_moon.get_solar_date(clip.start_time, day)
    return sun_moon.get_solar_event_time(date, event_name, day)


class AstronomicalDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Astronomical Dawn'


class AstronomicalDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Astronomical Dusk'


class CivilDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Civil Dawn'


class CivilDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Civil Dusk'


class DetectorNameMeasurement:
    
    name = 'Detector Name'
    
    def measure(self, clip):
        return model_utils.get_clip_detector_name(clip)
    
    
class DetectorTypeMeasurement:
     
    name = 'Detector Type'
     
    def measure(self, clip):
        return model_utils.get_clip_type(clip)
    
    
class DurationMeasurement:
    
    name = 'Duration'
    
    def measure(self, clip):
        return clip.duration
    
    
class EndIndexMeasurement:
    
    name = 'End Index'
    
    def measure(self, clip):
        return clip.end_index
    
    
class EndTimeMeasurement:
    
    name = 'End Time'
    
    def measure(self, clip):
        return clip.end_time
    
    
class IdMeasurement:
    
    name = 'ID'
    
    def measure(self, clip):
        return clip.id
    
    
class LengthMeasurement:
    
    name = 'Length'
    
    def measure(self, clip):
        return clip.length
    
    
class LunarAltitudeMeasurement:
    
    name = 'Lunar Altitude'
    
    def measure(self, clip):
        return _get_lunar_position(clip).altitude
    
    
def _get_lunar_position(clip):
    sun_moon = _get_sun_moon(clip)
    return sun_moon.get_lunar_position(clip.start_time)
    
    
def _get_sun_moon(clip):
    station = clip.station
    return _SUN_MOONS.get_sun_moon(
        station.latitude, station.longitude, station.tz)


class LunarAzimuthMeasurement:
    
    name = 'Lunar Azimuth'
    
    def measure(self, clip):
        return _get_lunar_position(clip).azimuth
    
    
class LunarIlluminationMeasurement:
    
    name = 'Lunar Illumination'
    
    def measure(self, clip):
        sun_moon = _get_sun_moon(clip)
        return sun_moon.get_lunar_illumination(clip.start_time)
    
    
class MicrophoneOutputNameMeasurement:
    
    name = 'Microphone Output Name'
    
    def measure(self, clip):
        return clip.mic_output.name
    
    
class NauticalDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Nautical Dawn'


class NauticalDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Nautical Dusk'


class PossibleRepeatedCallMeasurement:
    
    # This measurement assumes that clips of a given station, detector,
    # and classification are visited in order of increasing start time.
    
    name = 'Possible Repeated Call'
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        interval = settings.get('min_intercall_interval', 60)
        self._min_intercall_interval = TimeDelta(seconds=interval)
        
        names = settings.get('ignored_classifications', [])
        self._ignored_classifications = frozenset('Call.' + n for n in names)
        
        self._last_call_times = {}
        
        self._annotation_info = \
            AnnotationInfo.objects.get(name='Classification')
    
    def measure(self, clip):
        
        classification = \
            model_utils.get_clip_annotation_value(clip, self._annotation_info)
        
        if classification is None or not classification.startswith('Call.'):
            return None
        
        else:
            # clip is a call
            
            if classification in self._ignored_classifications:
                return None
            
            else:
                # classification should not be ignored
                
                detector_name = model_utils.get_clip_detector_name(clip)
                key = (clip.station.name, detector_name, classification)
                last_time = self._last_call_times.get(key)
                
                time = clip.start_time
                self._last_call_times[key] = time
                
                if last_time is None:
                    # first clip with this classification
                    
                    return False
                
                else:
                    # not first clip with this classification
                    
                    return time - last_time < self._min_intercall_interval
    
    
class RecordingChannelNumberMeasurement:
    
    name = 'Recording Channel Number'
    
    def measure(self, clip):
        return clip.channel_num


class RecordingDurationMeasurement:
    
    name = 'Recording Duration'
    
    def measure(self, clip):
        return clip.recording.duration
        
        
class RecordingEndTimeMeasurement:
    
    name = 'Recording End Time'
    
    def measure(self, clip):
        return clip.recording.end_time
    
    
class RecordingLengthMeasurement:
    
    name = 'Recording Length'
    
    def measure(self, clip):
        return clip.recording.length
    
    

class RecordingStartTimeMeasurement:
    
    name = 'Recording Start Time'
    
    def measure(self, clip):
        return clip.recording.start_time
    
    
_SOLAR_EVENT_NAMES = frozenset(SunMoon.SOLAR_EVENT_NAMES)


class _RelativeClipTimeMeasurement:
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        self._reference_name = settings.get(
            'reference_time', 'Recording Start Time')
        
        self._negate = settings.get('negate', False)
        
        if self._reference_name in _SOLAR_EVENT_NAMES:
            self._day = settings.get('day')
            if self._day is None:
                raise ValueError(
                    'Measurement settings lack required "day" item.')
    
    def measure(self, clip):
        
        reference_time = self._get_reference_time(clip)
        
        if reference_time is None:
            return None
        
        else:
            
            delta = self._get_clip_time(clip) - reference_time
            
            if self._negate:
                delta = -delta
                
            return delta.total_seconds()
    
    def _get_reference_time(self, clip):
        
        reference_name = self._reference_name
        
        if reference_name == 'Recording Start Time':
            return clip.recording.start_time
        
        elif reference_name == 'Recording End Time':
            return clip.recording.end_time
        
        else:
            return _get_solar_event_time(clip, reference_name, self._day)
    
    
class RelativeEndTimeMeasurement(_RelativeClipTimeMeasurement):
    
    name = 'Relative End Time'
    
    def _get_clip_time(self, clip):
        return clip.end_time
    
    
class RelativeStartTimeMeasurement(_RelativeClipTimeMeasurement):
    
    name = 'Relative Start Time'
    
    def _get_clip_time(self, clip):
        return clip.start_time
    
    
class SampleRateMeasurement:
    
    name = 'Sample Rate'
    
    def measure(self, clip):
        return clip.sample_rate
    
    
class SolarAltitudeMeasurement:
    
    name = 'Solar Altitude'
    
    def measure(self, clip):
        return _get_solar_position(clip).altitude
    
    
def _get_solar_position(clip):
    sun_moon = _get_sun_moon(clip)
    return sun_moon.get_solar_position(clip.start_time)
    
    
class SolarAzimuthMeasurement:
    
    name = 'Solar Azimuth'
    
    def measure(self, clip):
        return _get_solar_position(clip).azimuth
    
    
class SolarMidnightMeasurement(_SolarEventTimeMeasurement):
    name = 'Solar Midnight'
    
    
class SolarNoonMeasurement(_SolarEventTimeMeasurement):
    name = 'Solar Noon'
    
    
class StartIndexMeasurement:
    
    name = 'Start Index'
    
    def measure(self, clip):
        return clip.start_index
    
    
class StartTimeMeasurement:
    
    name = 'Start Time'
    
    def measure(self, clip):
        return clip.start_time
    
    
class StationNameMeasurement:
    
    name = 'Station Name'
    
    def measure(self, clip):
        return clip.station.name
    
    
class SolarPeriodMeasurement:
    
    name = 'Solar Period'
    
    def measure(self, clip):
        sun_moon = _get_sun_moon(clip)
        return sun_moon.get_solar_period_name(clip.start_time)


class SunriseMeasurement(_SolarEventTimeMeasurement):
    name = 'Sunrise'
    
    
class SunsetMeasurement(_SolarEventTimeMeasurement):
    name = 'Sunset'
    
    
_MEASUREMENT_CLASSES = dict((c.name, c) for c in [
    AnnotationValueMeasurement,
    AstronomicalDawnMeasurement,
    AstronomicalDuskMeasurement,
    CivilDawnMeasurement,
    CivilDuskMeasurement,
    DetectorNameMeasurement,
    DetectorTypeMeasurement,
    DurationMeasurement,
    EndIndexMeasurement,
    EndTimeMeasurement,
    IdMeasurement,
    LengthMeasurement,
    LunarAltitudeMeasurement,
    LunarAzimuthMeasurement,
    LunarIlluminationMeasurement,
    MicrophoneOutputNameMeasurement,
    NauticalDawnMeasurement,
    NauticalDuskMeasurement,
    PossibleRepeatedCallMeasurement,
    RecordingChannelNumberMeasurement,
    RecordingDurationMeasurement,
    RecordingEndTimeMeasurement,
    RecordingLengthMeasurement,
    RecordingStartTimeMeasurement,
    RelativeEndTimeMeasurement,
    RelativeStartTimeMeasurement,
    SampleRateMeasurement,
    SolarAltitudeMeasurement,
    SolarAzimuthMeasurement,
    SolarMidnightMeasurement,
    SolarNoonMeasurement,
    StartIndexMeasurement,
    StartTimeMeasurement,
    StationNameMeasurement,
    SolarPeriodMeasurement,
    SunriseMeasurement,
    SunsetMeasurement
])


_NO_VALUE_STRING = ''

_DEFAULT_DATE_FORMAT = '%Y-%m-%d'
_DEFAULT_TIME_FORMAT = '%H:%M:%S'
_DEFAULT_DATE_TIME_FORMAT = _DEFAULT_DATE_FORMAT + ' ' + _DEFAULT_TIME_FORMAT
_DEFAULT_DURATION_FORMAT = '%h:%M:%S'
_DEFAULT_TIME_DIFFERENCE_FORMAT = '%g%h:%M:%S'

_TEST_DATE_TIME = DateTime(2020, 1, 1)


class BooleanFormatter:
    
    name = 'Boolean Formatter'
    
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        elif value:
            return 'True'
        else:
            return 'False'
    
    
class CallSpeciesFormatter:
    
    name = 'Call Species Formatter'
    
    def format(self, classification, clip):
        prefix = 'Call.'
        if classification is None or not classification.startswith(prefix):
            return _NO_VALUE_STRING
        else:
            return classification[len(prefix):]
        
           
class DecimalFormatter:
    
    name = 'Decimal Formatter'
    
    def __init__(self, settings=None):
        if settings is None:
            self._format = '{:f}'
        else:
            self._format = '{:' + settings.get('detail', '') + 'f}'
            
    def format(self, x, clip):
        return self._format.format(x)


class _DateTimeFormatter:
    
    def __init__(self, local, settings=None):
        
        self._local = local
        
        if settings is None:
            settings = {}
        
        self._formatter = self._get_formatter(settings)
        self._round, self._rounding_increment, self._rounding_mode = \
            _get_rounding(settings, False, self._formatter.min_time_increment)
    
    def _get_formatter(self, settings):
        
        format_ = settings.get('format', _DEFAULT_DATE_TIME_FORMAT)
        
        # Try format string on test `DateTime` and raise an exception
        # if there's a problem.
        try:
            _TEST_DATE_TIME.strftime(format_)
        except Exception as e:
            raise ValueError(
                f'Could not format test time with "{format_}". '
                f'Error message was: {str(e)}')
        
        return DateTimeFormatter(format_)
    
    def format(self, dt, clip):
        
        if dt is None:
            return _NO_VALUE_STRING
        
        else:
            
            # Round time if needed.
            if self._round:
                dt = time_utils.round_datetime(
                    dt, self._rounding_increment, self._rounding_mode)
                
            # Get local time if needed.
            if self._local:
                time_zone = clip.station.tz
                dt = dt.astimezone(time_zone)
            
            # Get time string.
            return self._formatter.format(dt)


def _get_rounding(settings, default_round, default_increment):
    
    round_ = settings.get('round')
    increment = settings.get('rounding_increment')
    mode = settings.get('rounding_mode')

    if round_ is None:
        round_ = default_round or increment is not None or mode is not None
        
    if round_:
        
        if increment is None:
            increment = default_increment
            if increment is None:
                increment = 1e-6
                
        if mode is None:
            mode = 'nearest'
    
    return round_, increment, mode


class LocalTimeFormatter(_DateTimeFormatter):
    
    name = 'Local Time Formatter'
    
    def __init__(self, settings=None):
        super().__init__(True, settings)
    
    
class LowerCaseFormatter:
    
    name = 'Lower Case Formatter'
    
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        else:
            return value.lower()
    
    
class ValueMapper:
    
    name = 'Value Mapper'
    
    def __init__(self, settings=None):
        if settings is None:
            self._mapping = {}
        else:
            self._mapping = settings.get('mapping', {})
            
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        else:
            return self._mapping.get(value, value)
    
    
class NocturnalBirdMigrationSeasonFormatter:
    
    name = 'Nocturnal Bird Migration Season Formatter'
        
    def format(self, time, clip):
        if time is None:
            return _NO_VALUE_STRING
        else:
            night = clip.station.get_night(time)
            return 'Fall' if night.month >= 7 else 'Spring'
    
    
class PercentFormatter(DecimalFormatter):
    
    name = 'Percent Formatter'
    
    def format(self, x, clip):
        return self._format.format(100 * x)


class SolarDateFormatter:
    
    name = 'Solar Date Formatter'
    
    def __init__(self, settings):
        self._day = settings.get('day')
        if self._day is None:
            raise ValueError('Measurement settings lack required "day" item.')
        self._format = settings.get('format', _DEFAULT_DATE_FORMAT)
    
    def format(self, time, clip):
        
        if time is None:
            return _NO_VALUE_STRING
        
        else:
            
            # Get solar day or night.
            sun_moon = _get_sun_moon(clip)
            date = sun_moon.get_solar_date(time, self._day)
            
            # Format date.
            return date.strftime(self._format)


class TimeDifferenceFormatter:

    name = 'Time Difference Formatter'
    
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self._negate = settings.get('negate', False)
        self._formatter = self._get_formatter(settings)
        self._round, self._rounding_increment, self._rounding_mode = \
            _get_rounding(settings, True, self._formatter.min_time_increment)
    
    def _get_formatter(self, settings):
        _format = settings.get('format', _DEFAULT_TIME_DIFFERENCE_FORMAT)
        return TimeDifferenceFormatter_(_format)
    
    def format(self, difference, clip):
        
        if difference is None:
            return _NO_VALUE_STRING
        
        else:
            
            # Negate difference if needed.
            if self._negate:
                difference = -difference
                
            # Round difference if needed.
            if self._round:
                td = TimeDelta(seconds=difference)
                rounded_td = time_utils.round_timedelta(
                    td, self._rounding_increment, self._rounding_mode)
                difference = rounded_td.total_seconds()
                
            return self._formatter.format(difference)


class UtcTimeFormatter(_DateTimeFormatter):
    
    name = 'UTC Time Formatter'
    
    def __init__(self, settings=None):
        super().__init__(False, settings)
            
    
_FORMATTER_CLASSES = dict((c.name, c) for c in [
    BooleanFormatter,
    CallSpeciesFormatter,
    DecimalFormatter,
    LocalTimeFormatter,
    LowerCaseFormatter,
    ValueMapper,
    NocturnalBirdMigrationSeasonFormatter,
    PercentFormatter,
    SolarDateFormatter,
    TimeDifferenceFormatter,
    UtcTimeFormatter,
])
