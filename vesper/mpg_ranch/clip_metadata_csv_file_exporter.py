"""Module containing class `ClipMetadataCsvFileExporter`."""


from datetime import (
    datetime as DateTime,
    time as Time,
    timedelta as TimeDelta)
from pathlib import Path
import csv
import tempfile

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import AnnotationInfo
from vesper.ephem.sun_moon import SunMoon, SunMoonCache
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Add "Relative End Time" measurement.

# TODO: Replace "Night" measurement with "Date" measurement.

# TODO: Add "Calling Rate" measurement.

# TODO: Consider changing default DateTime format.

# TODO: Add `fractional_digits` time and duration setting.

# TODO: Support time and duration rounding.

# TODO: Make each archive either day-oriented or night-oriented, with
# orientation specified in "Archive Settings.yaml". Make `day` setting
# optional for solar event measurements and use day/night orientation
# to determine default value.

# TODO: Implement table format presets.

# TODO: Use `jsonschema` package to check table format specification.

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
    Night
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
    + Date
    - Night
    Start Time
    End Time
    Relative Start Time
    + Relative End Time
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


_TABLE_FORMAT = yaml_utils.load('''

columns:

    - name: season
      measurement: Start Time
      format: Nocturnal Bird Migration Season
  
    - name: year
      measurement: Start Time
      format:
          name: Night
          settings:
              format: "%Y"

    - name: detector
      measurement: Detector Type
      format: Lower Case

    - name: species
      measurement:
          name: Annotation Value
          settings:
              annotation_name: Classification
      format:
          - Call Species
          - name: Mapping
            settings:
                items:
                    DoubleUp: dbup
                    Other: othe
                    Unknown: unkn
          - Lower Case
      
    - name: site
      measurement: Station Name
      format:
          name: Mapping
          settings:
              items:
                  Baldy: baldy
                  Floodplain: flood
                  Ridge: ridge
                  Sheep Camp: sheep
      
    - name: date
      measurement: Start Time
      format:
          name: Night
          settings:
              format: "%m/%d/%y"
              
    - name: recording_start
      measurement: Recording Start Time
      format: Local Time
      
    - name: recording_length
      measurement: Recording Duration
      format: Duration
              
    - name: detection_time
      measurement: Relative Start Time
      format: Duration
      
    - name: real_detection_time
      measurement: Start Time
      format:
          name: Local Time
          settings:
              format: "%H:%M:%S"
              
    - name: real_detection_time
      measurement: Start Time
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
              
    - name: rounded_to_half_hour
      measurement: Start Time
      format:
          name: Local Time
          settings:
              rounding_increment: 1800
      
    - name: duplicate
      measurement:
          name: Possible Repeated Call
          settings:
              min_intercall_interval: 60
              ignored_classifications: [Other, Unknown, Weak]
      format:
          - Boolean
          - name: Mapping
            settings:
                items:
                    'True': 'yes'
                    'False': 'no'
    
    - name: sunset
      measurement:
          name: Sunset
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dusk
      measurement:
          name: Civil Dusk
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dusk
      measurement:
          name: Nautical Dusk
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dusk
      measurement:
          name: Astronomical Dusk
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: astronomical_dawn
      measurement:
          name: Astronomical Dawn
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: nautical_dawn
      measurement:
          name: Nautical Dawn
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: civil_dawn
      measurement:
          name: Civil Dawn
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: sunrise
      measurement:
          name: Sunrise
          settings:
              day: False
      format:
          name: Local Time
          settings:
              format: "%m/%d/%y %H:%M:%S"
      
    - name: moon_altitude
      measurement: Lunar Altitude
      format:
          name: Decimal
          settings:
              detail: ".1"

    - name: moon_illumination
      measurement: Lunar Illumination
      format:
          name: Percent
          settings:
              detail: ".1"
''')


#     - name: twilight
#       measurement: Solar Period
#       format:
#           name: Mapping
#           settings:
#               items:
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
#       format:
#           name: Mapping
#           settings:
#               items:
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
#     - Recording End Time
#     - Recording Duration
#     - Recording Length
#     - Recording Channel Number
#     - ID
#     - Start Time
#     - End Time
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
              negate: True
      format: Duration
    
    - name: Time After Sunset
      measurement:
          name: Relative Start Time
          settings:
              reference_time: Sunset
              day: False
      format: Duration

    - name: Time Before Sunrise
      measurement:
          name: Relative Start Time
          settings:
              reference_time: Sunrise
              day: False
              negate: True
      format: Duration
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
        format_ = None
    
    else:
        # `column` is not string
        
        # We assume that `column` is a `dict`.
        
        name, measurement = \
            _get_column_name_and_measurement(column, column_num)
        format_ = _get_column_format(column, name)
    
    return Bunch(name=name, measurement=measurement, format=format_)


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


def _get_column_format(column, name):
    
    try:
        
        format_ = column.get('format')
        
        if format_ is None:
            return None
        
        elif isinstance(format_, (list, tuple)):
            # sequence of format specifications
            
            return [_get_format(f) for f in format_]
        
        else:
            # single format specification
            
            return _get_format(format_)
    
    except Exception as e:
        raise CommandExecutionError(f'For column "{name}": {str(e)}')


def _get_format(format_):
    
    if isinstance(format_, str):
        # string format name
        
        cls = _get_format_class(format_)
        return cls()
        
    else:
        # `dict` format specification
        
        name = _get_format_name(format_)
        cls = _get_format_class(name)
        settings = format_.get('settings')
        if settings is None:
            return cls()
        else:
            return cls(settings)
    
    
def _get_format_class(name):
    try:
        return _FORMAT_CLASSES[name]
    except KeyError:
        raise CommandExecutionError(
            f'Unrecognized format name "{name}".')


def _get_format_name(format_):
    try:
        return format_['name']
    except KeyError:
        raise CommandExecutionError(
            'Format specification is missing required "name" item.')


def _get_column_value(column, clip):
    
    value = column.measurement.measure(clip)
    
    format_ = column.format
    
    if format_ is None:
        return str(value)
    
    elif isinstance(format_, (list, tuple)):
        # sequence of formats
        
        for f in format_:
            value = f.format(value, clip)
        return value
            
    else:
        # single format
        
        return format_.format(value, clip)
    
    
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


class NightMeasurement:
    
    name = 'Night'
    
    def measure(self, clip):
        return clip.date
    
    
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
        return TimeDelta(seconds=clip.recording.duration)
        
        
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


class RelativeStartTimeMeasurement:
    
    name = 'Relative Start Time'
    
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
            
            delta = clip.start_time - reference_time
            
            if self._negate:
                delta = -delta
                
            return delta
    
    def _get_reference_time(self, clip):
        
        reference_name = self._reference_name
        
        if reference_name == 'Recording Start Time':
            return clip.recording.start_time
        
        elif reference_name == 'Recording End Time':
            return clip.recording.end_time
        
        else:
            return _get_solar_event_time(clip, reference_name, self._day)
    
    
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
    NightMeasurement,
    PossibleRepeatedCallMeasurement,
    RecordingChannelNumberMeasurement,
    RecordingDurationMeasurement,
    RecordingEndTimeMeasurement,
    RecordingLengthMeasurement,
    RecordingStartTimeMeasurement,
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

_TEST_DATETIME = DateTime(2020, 1, 1)


class BooleanFormat:
    
    name = 'Boolean'
    
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        elif value:
            return 'True'
        else:
            return 'False'
    
    
class CallSpeciesFormat:
    
    name = 'Call Species'
    
    def format(self, classification, clip):
        prefix = 'Call.'
        if classification is None or not classification.startswith(prefix):
            return _NO_VALUE_STRING
        else:
            return classification[len(prefix):]
        
           
class DecimalFormat:
    
    name = 'Decimal'
    
    def __init__(self, settings=None):
        if settings is None:
            self._format = '{:f}'
        else:
            self._format = '{:' + settings.get('detail', '') + 'f}'
            
    def format(self, x, clip):
        return self._format.format(x)


class DurationFormat:

    name = 'Duration'
    
    def __init__(self, settings=None):
        
        if settings is None:
            self._format = '{:d}:{:02d}:{:02d}'
 
        else:
            
            sep = settings.get('separator', ':')
            num_hours_digits = settings.get('num_hours_digits')
            
            if num_hours_digits is None:
                hours_format = '{:d}'
            else:
                hours_format = '{:0' + str(num_hours_digits) + '}'
                
            self._format = hours_format + sep + '{:02d}' + sep + '{:02d}'
        
    def format(self, duration, clip):
        
        if duration is None:
            return _NO_VALUE_STRING
        
        else:
            
            seconds = duration.total_seconds()
            
            if seconds < 0:
                seconds = -seconds
                prefix = '-'
            else:
                prefix = ''
            
            hours = int(seconds // 3600)
            seconds -= hours * 3600
            
            minutes = int(seconds // 60)
            seconds -= minutes * 60
            
            seconds = int(round(seconds))
            
            return prefix + self._format.format(hours, minutes, seconds)


class _TimeFormat:
    
    def __init__(self, local, settings=None):
        
        self._local = local
        
        if settings is None:
            settings = {}
        
        self._format = self._get_format(settings)
        self._rounding_increment = settings.get('rounding_increment', None)
    
    def _get_format(self, settings):
        
        format_ = settings.get('format')
        
        if format_ is None:
            return '%H:%M:%S'
        
        else:
            # format string provided
            
            # Try format string on test `datetime` and raise an exception
            # if there's a problems.
            try:
                _TEST_DATETIME.strftime(format_)
            except Exception as e:
                raise ValueError(
                    f'Could not format test time with "{format_}". '
                    f'Error message was: {str(e)}')
            
            return format_
    
    def format(self, time, clip):
        
        if time is None:
            return _NO_VALUE_STRING
        
        else:
            
            # Round time if needed.
            if self._rounding_increment is not None:
                time = _round_time(time, self._rounding_increment)
                
            # Get local time if needed.
            if self._local:
                time_zone = clip.station.tz
                time = time.astimezone(time_zone)
            
            # Get time string.
            return time.strftime(self._format)
           

# TODO: Use `time_utils.round_datetime` and `time_utils.round_time`
# here to allow rounding increments larger than one hour. Note that
# some times in the middles of increments might round differently
# afterward. Would that be a problem?
# TODO: Perhaps require that rounding increment evenly divide 24 hours?
# TODO: Add support for different rounding modes, so that, for
# example, one could round down or up to nearest hour as well as to
# nearest hour.
def _round_time(time, increment):
    
    if isinstance(time, (DateTime, Time)):
                  
        seconds_after_the_hour = time.minute * 60 + time.second
        
        time = time.replace(minute=0, second=0, microsecond=0)
        
        increments = int(round(seconds_after_the_hour / increment))
        delta = TimeDelta(seconds=increments * increment)
        
        return time + delta


class LocalTimeFormat(_TimeFormat):
    
    name = 'Local Time'
    
    def __init__(self, settings=None):
        super().__init__(True, settings)
    
    
class LowerCaseFormat:
    
    name = 'Lower Case'
    
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        else:
            return value.lower()
    
    
class MappingFormat:
    
    name = 'Mapping'
    
    def __init__(self, settings=None):
        if settings is None:
            self._mapping = {}
        else:
            self._mapping = settings.get('items', {})
            
    def format(self, value, clip):
        if value is None:
            return _NO_VALUE_STRING
        else:
            return self._mapping.get(value, value)
    
    
class NightFormat:
    
    name = 'Night'
    
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self._format = settings.get('format', '%H:%M:%S')
    
    def format(self, time, clip):
        
        if time is None:
            return _NO_VALUE_STRING
        
        else:
            
            # Get local night.
            night = clip.station.get_night(time)
            
            # Get night string.
            return night.strftime(self._format)


class NocturnalBirdMigrationSeasonFormat:
    
    name = 'Nocturnal Bird Migration Season'
        
    def format(self, time, clip):
        if time is None:
            return _NO_VALUE_STRING
        else:
            night = clip.station.get_night(time)
            return 'Fall' if night.month >= 7 else 'Spring'
    
    
class PercentFormat(DecimalFormat):
    
    name = 'Percent'
    
    def format(self, x, clip):
        return self._format.format(100 * x)


class UtcTimeFormat(_TimeFormat):
    
    name = 'UTC Time'
    
    def __init__(self, settings=None):
        super().__init__(False, settings)
            
    
_FORMAT_CLASSES = dict((c.name, c) for c in [
    BooleanFormat,
    CallSpeciesFormat,
    DecimalFormat,
    DurationFormat,
    LocalTimeFormat,
    LowerCaseFormat,
    MappingFormat,
    NightFormat,
    NocturnalBirdMigrationSeasonFormat,
    PercentFormat,
    UtcTimeFormat,
])
