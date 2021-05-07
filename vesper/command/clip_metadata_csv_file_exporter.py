"""Module containing class `ClipMetadataCsvFileExporter`."""


from collections import defaultdict, deque
from datetime import timedelta as TimeDelta
from pathlib import Path
import csv
import logging
import tempfile

from vesper.command.command import CommandExecutionError
from vesper.django.app.models import AnnotationInfo
from vesper.ephem.sun_moon import SunMoon, SunMoonCache
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.preset_manager import preset_manager
from vesper.singleton.recording_manager import recording_manager
from vesper.util.bunch import Bunch
from vesper.util.calculator import Calculator as Calculator_
from vesper.util.datetime_formatter import DateTimeFormatter
from vesper.util.time_difference_formatter import TimeDifferenceFormatter
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.util.yaml_utils as yaml_utils


# TODO: Figure out some way to be able to specify globally that
# measurements and formatters should be diurnal or nocturnal.
# A `default settings` list might be good, with each item an
# associative array with `scope` and `settings` items. The `scope`
# item could be one of "All" (for all measurements and formatters),
# "Measurements" (for all measurements), "Formatters" (for all
# formatters), or a list of measurement and/or formatter names.
# The order of arrays in the list would determine precedence.

# TODO: Use `jsonschema` package to check table format specification.

# TODO: Consider supporting default format specification in measurement
# classes.

# TODO: Consider supporting user-defined formatters. These would appear
# in a YAML `formatters` associated array that accompanies the `columns`
# array. The `formatters` array would map user-defined formatter names
# to formatter specifications.

# TODO: Consider supporting specification of default formatters by
# value type. This might take the form of a YAML `default_formatters`
# associative array that accompanies the `columns` array. The
# `default_formatters` array would map value type names to formatter
# specifications. Vesper would define a limited number of value types,
# e.g. String, Integer, Float, and DateTime. Would measurements be
# able to define their own types? Maybe not initially, at least.

# TODO: Consider supporting "Python Expression Evaluator" and
# "Python Function Executor" formatters. The expression evaluator
# would evaluate a Python expression provided as a text setting.
# The expression would refer to the value for be formatted as the
# variable "x". The value of the expression would be the formatter's
# result. The "Python Function Executor" formatter would execute a
# Python function provided as a text setting. The function would
# take a single argument, a value to be formatted, and return the
# formatted result. For both formatters, the provided Python code
# would have access to the `math` module and the Python builtin
# functions without importing anything themselves. Functions could
# also import additional modules. This would be very convenient, but
# note that it could also be dangerous in public archives, because
# of the risk of code injection attacks. Perhaps these would be
# plugins that would be omitted when serving public archives.


'''
A *measurement* produces a value from a clip. The value may be computed
from the samples of the clip, or it may not. Currently, all implemented
measurements make no use of clip samples.

The name of a measurement describes the property of a clip that the
measurement computes. Words in the name are capitalized and separated
by spaces. The basic idea is that measurement names should look good
in a list presented to a user. The class name of a measurement is
formed by concatenating the words of the measurement's name, lowering
the case of any letters that are not word-initial (e.g. "ID" becomes
"Id") and appending "Measurement".

Some examples of (class name, measurement name) pairs:

    (AnnotationValueMeasurement, Annotation Value)
    (AstronomicalDawnMeasurement, Astronomical Dawn)
    (IdMeasurement, ID)
    (LengthMeasurement, Length)
    (StartIndexMeasurement, Start Index)

A *formatter* transforms a value computed by a measurement or another
formatter, for example for inclusion in a clip table. Most formatters
produce string values, but some do not. Unlike measurements, formatters
can be composed in sequence, to transform a measurement value in more
than one step.

The name of a formatter describes the "occupation" of the formatter,
for example "Local Time Formatter" or "Calculator". The name follows
the same capitalization and spacing conventions as the name of a
measurement. Many formatters format values as strings, and most
such formatters have names of the form "<value type> Formatter",
where <value type> is either the type of input value (e.g.
"Duration Formatter" and "Relative Time Formatter") or the way
in which the output presents the input value (e.g.
"Decimal Formatter", "Local Time Formatter", or
"Lower Case Formatter"). However, the occupations of some
formatters are best described in other terms, and so have names
that do not end in "Formatter". Examples of such names include
"Calculator", "Prefix Remover", and "Value Mapper". The class
name of a formatter is formed by concatenating the words of the
measurement's name and lowering the case of any letters that are
not word-initial.

The inconsistency in the naming conventions for measurements
(whose names never end in "Measurement") and formatters (whose
names most often end in "Formatter") is undesirable, but seemed
the least undesirable of the various alternatives considered. For
example, including "Measurement" in all measurement names would
make lists of those names look awkward, while omitting "Formatter"
from formatter names would introduce inconsistencies in what the
names denote, making formatter specifications awkward and
confusing.
'''


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
    End Index
    End Time
    First Recording File Duration Measurement
    First Recording File End Index Measurement
    First Recording File End Time Measurement
    First Recording File Length Measurement
    First Recording File Name Measurement
    First Recording File Number Measurement
    First Recording File Path Measurement
    First Recording File Start Index Measurement
    First Recording File Start Time Measurement
    ID
    Last Recording File Duration Measurement
    Last Recording File End Index Measurement
    Last Recording File End Time Measurement
    Last Recording File Length Measurement
    Last Recording File Name Measurement
    Last Recording File Number Measurement
    Last Recording File Path Measurement
    Last Recording File Start Index Measurement
    Last Recording File Start Time Measurement
    Length
    Lunar Altitude
    Lunar Azimuth
    Lunar Illumination
    Microphone Output Name
    Nautical Dawn
    Nautical Dusk
    Recent Clip Count
    Recording Channel Number
    Recording Duration
    Recording End Time
    Recording Length
    Recording Start Time
    Relative End Time
    Relative Start Time
    Sample Rate
    Sensor Name
    Solar Altitude
    Solar Azimuth
    Solar Midnight
    Solar Noon
    Solar Period
    Start Index
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

Recording Files:
    First Recording File Duration Measurement
    First Recording File End Index Measurement
    First Recording File End Time Measurement
    First Recording File Length Measurement
    First Recording File Name Measurement
    First Recording File Number Measurement
    First Recording File Path Measurement
    First Recording File Start Index Measurement
    First Recording File Start Time Measurement
    Last Recording File Duration Measurement
    Last Recording File End Index Measurement
    Last Recording File End Time Measurement
    Last Recording File Length Measurement
    Last Recording File Name Measurement
    Last Recording File Number Measurement
    Last Recording File Path Measurement
    Last Recording File Start Index Measurement
    Last Recording File Start Time Measurement

Clip:
    ID
    Station Name
    Microphone Output Name
    Sensor Name
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
    Recent Clip Count

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


'''
Formatter classes:
    Calculator (Any -> Number)
    DecimalFormatter (Number -> String)
    DurationFormatter (Number -> String)
    LocalTimeFormatter (DateTime -> String)
    LowerCaseFormatter (String -> String)
    PercentFormatter (Number -> String)
    PrefixRemover (String -> String)
    RelativeTimeFormatter (Number -> String)
    SolarDateFormatter (DateTime -> String)
    UpperCaseFormatter (String -> String)
    UtcTimeFormatter (DateTime -> String)
    ValueMapper (Any -> Any)

All formatters but `ValueMapper` automatically map `None` to `None`.

By default, `ValueMapper` maps keys for which values are not specified
to themselves, so it maps `None` to `None`. A different value for `None`
can be specified explicitly just as for any other key.

`ValueMapper` has a `default` setting that allows specification of a
default mapping value. When this setting is present, keys for which
values are not specified in the `mapping` setting are mapped to the
default.
'''


_FALLBACK_TABLE_FORMAT = yaml_utils.load('''

columns:

    - name: Sensor
      measurement: Sensor Name

    - name: Detector
      measurement: Detector Name
    
    - measurement: Start Time
      formatter:
          name: Local Time Formatter
          settings: {format: "%Y-%m-%d %H:%M:%S.%3f"}
    
    - measurement: Duration
      formatter:
          name: Decimal Formatter
          settings: {detail: ".3"}
    
    - name: Classification
      measurement:
          name: Annotation Value
          settings: {annotation_name: Classification}

''')
"""Table format used when presets are not available."""


_SUN_MOONS = SunMoonCache()


class ClipMetadataCsvFileExporter:
    
    
    extension_name = 'Clip Metadata CSV File Exporter'
    
    _OUTPUT_CHUNK_SIZE = 100
    
    
    def __init__(self, args):
        
        get = command_utils.get_required_arg
        self._table_format_name = get('table_format', args)
        self._output_file_path = get('output_file_path', args)
        
        self._table_format = _get_table_format(self._table_format_name)
        self._columns = _create_table_columns(self._table_format)
        self._rows = []
    
    
    def begin_exports(self):
        self._open_output_file()
        column_names = [c.name for c in self._columns]
        self._write_row(column_names)
    
    
    def _open_output_file(self):
        
        # Create output file in temporary file directory.
        try:
            self._output_file = tempfile.NamedTemporaryFile(
                'wt', newline='', prefix='vesper-', suffix='.csv',
                delete=False)
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
            os_utils.copy_file(temp_file_path, self._output_file_path)
        except Exception as e:
            self._handle_output_error('Could not rename output file.', e)
    
    
def _get_table_format(table_format_name):
    
    if table_format_name == '':
        # no table format name
        
        return _FALLBACK_TABLE_FORMAT
    
    else:
        # have table format name
        
        preset_path = ('Clip Table Format', table_format_name)
        preset = preset_manager.get_preset(preset_path)
        return preset.data


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
    return _format_value(value, clip, column.formatter)


def _format_value(value, clip, formatter):
    
    if formatter is not None:
    
        if isinstance(formatter, (list, tuple)):
            # sequence of formatters
            
            for f in formatter:
                value = f.format(value, clip)
                
        else:
            # single formatter
            
            value = formatter.format(value, clip)
    
    if value is None:
        return _NO_VALUE_STRING
    
    elif not isinstance(value, str):
        return str(value)
    
    else:
        return value
    
    
class Measurement:
    
    def _get_required_setting(self, settings, name):
        try:
            return settings[name]
        except KeyError:
            raise CommandExecutionError(
                f'Measurement settings lack required "{name}" item.')
    
    def measure(self, clip):
        raise NotImplementedError()


class AnnotationValueMeasurement(Measurement):
    
    name = 'Annotation Value'
    
    def __init__(self, settings):
        annotation_name = \
            self._get_required_setting(settings, 'annotation_name')
        self._annotation_info = \
            AnnotationInfo.objects.get(name=annotation_name)
    
    def measure(self, clip):
        return model_utils.get_clip_annotation_value(
            clip, self._annotation_info)
        

class _SolarEventTimeMeasurement(Measurement):
    
    def __init__(self, settings):
        self._diurnal = self._get_required_setting(settings, 'diurnal')
        
    def measure(self, clip):
        return _get_solar_event_time(clip, self.name, self._diurnal)


def _get_solar_event_time(clip, event_name, day):
    sun_moon = _get_sun_moon(clip)
    date = sun_moon.get_solar_date(clip.start_time, day)
    return sun_moon.get_solar_event_time(date, event_name, day)


def _get_sun_moon(clip):
    station = clip.station
    return _SUN_MOONS.get_sun_moon(
        station.latitude, station.longitude, station.tz)


class AstronomicalDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Astronomical Dawn'


class AstronomicalDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Astronomical Dusk'


class CivilDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Civil Dawn'


class CivilDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Civil Dusk'


class DetectorNameMeasurement(Measurement):
    
    name = 'Detector Name'
    
    def measure(self, clip):
        return model_utils.get_clip_detector_name(clip)
    
    
class DetectorTypeMeasurement(Measurement):
     
    name = 'Detector Type'
     
    def measure(self, clip):
        return model_utils.get_clip_type(clip)
    
    
class DurationMeasurement(Measurement):
    
    name = 'Duration'
    
    def measure(self, clip):
        return clip.duration
    
    
class _IndexMeasurement(Measurement):
    
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self._reference_name = \
            settings.get('reference_index', self._default_reference_index_name)
    
    def measure(self, clip):
        
        clip_index = self._get_index(clip)
        
        if clip_index is None:
            return None
        
        reference_index = self._get_reference_index(clip)
        
        if reference_index is None:
            return None
        
        # If we get here, we have both a clip index and a reference index.
        
        return clip_index - reference_index
    
    def _get_reference_index(self, clip):
        
        reference_name = self._reference_name
        
        if reference_name == 'Recording Start Index':
            return 0
        
        elif reference_name == 'Recording End Index':
            return clip.recording.length
        
        elif reference_name == self._recording_file_start_index_reference_name:
            return self._get_recording_file_reference_index(clip, 'start')
        
        else:
            return self._get_recording_file_reference_index(clip, 'end')
    
    def _get_recording_file_reference_index(self, clip, name):
        info = _get_recording_file_info(clip)
        if info is None:
            return None
        else:
            recording_file = info[0][self._recording_file_index]
            return getattr(recording_file, name + '_index')


def _get_recording_file_info(clip):
    
    try:
        return clip_manager.get_recording_file_info(clip)
    
    except Exception as e:
        
        logging.warning(
            f'Could not get recording file information for clip '
            f'{str(clip)}. Error message was: {str(e)}')
        
        return None


class EndIndexMeasurement(_IndexMeasurement):
    
    name = 'End Index'
    
    _default_reference_index_name = 'Recording Start Index'
    
    _recording_file_start_index_reference_name = \
        'Last Recording File Start Index'
    
    _recording_file_end_index_reference_name = \
        'Last Recording File End Index'
    
    _recording_file_index = -1
    
    def _get_index(self, clip):
        return clip.end_index


class EndTimeMeasurement(Measurement):
    
    name = 'End Time'
    
    def measure(self, clip):
        return clip.end_time
    
    
class _RecordingFileMeasurement(Measurement):
    
    def measure(self, clip):
        info = _get_recording_file_info(clip)
        if info is None:
            return None
        else:
            recording_file = info[0][self._file_index]
            return self._measure(recording_file)
    
    def _measure(self, recording_file):
        raise NotImplementedError()


class _RecordingFileDurationMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.duration


class _RecordingFileEndIndexMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.end_index


class _RecordingFileEndTimeMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.end_time


class _RecordingFileLengthMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.length


class _RecordingFileNameMeasurement(_RecordingFileMeasurement):
    
    def _measure(self, recording_file):
        path = recording_file.path
        if path is None:
            return None
        else:
            return Path(path).name


class _RecordingFileNumberMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.file_num


class _RecordingFilePathMeasurement(_RecordingFileMeasurement):
    
    def __init__(self, settings=None):
        if settings is None:
            settings = {}
        self._absolute = settings.get('absolute', True)
    
    def _measure(self, recording_file):
        
        relative_path = recording_file.path
        
        if relative_path is None:
            
            # TODO: Can this really happen? Why would we have a file
            # without a path?
            return None
        
        elif self._absolute:
            
            rm = recording_manager
            
            try:
                return rm.get_absolute_recording_file_path(relative_path)
            
            except Exception as e:
                logging.warning(
                    f'Could not get absolute path for recording file '
                    f'"{relative_path}". Error message was: {str(e)}')
                return None
        
        else:
            return relative_path


class _RecordingFileStartIndexMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.start_index


class _RecordingFileStartTimeMeasurement(_RecordingFileMeasurement):
    def _measure(self, recording_file):
        return recording_file.start_time


class _First:
    """Provides file index to first recording file measurements."""
    _file_index = 0


class FirstRecordingFileDurationMeasurement(
        _RecordingFileDurationMeasurement, _First):
    name = 'First Recording File Duration'


class FirstRecordingFileEndIndexMeasurement(
        _RecordingFileEndIndexMeasurement, _First):
    name = 'First Recording File End Index'


class FirstRecordingFileEndTimeMeasurement(
        _RecordingFileEndTimeMeasurement, _First):
    name = 'First Recording File End Time'


class FirstRecordingFileLengthMeasurement(
        _RecordingFileLengthMeasurement, _First):
    name = 'First Recording File Length'


class FirstRecordingFileNameMeasurement(
        _RecordingFileNameMeasurement, _First):
    name = 'First Recording File Name'


class FirstRecordingFileNumberMeasurement(
        _RecordingFileNumberMeasurement, _First):
    name = 'First Recording File Number'
    
    
class FirstRecordingFilePathMeasurement(
        _RecordingFilePathMeasurement, _First):
    name = 'First Recording File Path'


class FirstRecordingFileStartIndexMeasurement(
        _RecordingFileStartIndexMeasurement, _First):
    name = 'First Recording File Start Index'


class FirstRecordingFileStartTimeMeasurement(
        _RecordingFileStartTimeMeasurement, _First):
    name = 'First Recording File Start Time'


class IdMeasurement(Measurement):
    
    name = 'ID'
    
    def measure(self, clip):
        return clip.id
    
    
class _Last:
    """Provides file index to last recording file measurements."""
    _file_index = -1
    
    
class LastRecordingFileDurationMeasurement(
        _RecordingFileDurationMeasurement, _Last):
    name = 'Last Recording File Duration'


class LastRecordingFileEndIndexMeasurement(
        _RecordingFileEndIndexMeasurement, _Last):
    name = 'Last Recording File End Index'


class LastRecordingFileEndTimeMeasurement(
        _RecordingFileEndTimeMeasurement, _Last):
    name = 'Last Recording File End Time'


class LastRecordingFileLengthMeasurement(
        _RecordingFileLengthMeasurement, _Last):
    name = 'Last Recording File Length'


class LastRecordingFileNameMeasurement(
        _RecordingFileNameMeasurement, _Last):
    name = 'Last Recording File Name'


class LastRecordingFileNumberMeasurement(
        _RecordingFileNumberMeasurement, _Last):
    name = 'Last Recording File Number'
    
    
class LastRecordingFilePathMeasurement(
        _RecordingFilePathMeasurement, _Last):
    name = 'Last Recording File Path'


class LastRecordingFileStartIndexMeasurement(
        _RecordingFileStartIndexMeasurement, _Last):
    name = 'Last Recording File Start Index'


class LastRecordingFileStartTimeMeasurement(
        _RecordingFileStartTimeMeasurement, _Last):
    name = 'Last Recording File Start Time'


class LengthMeasurement(Measurement):
    
    name = 'Length'
    
    def measure(self, clip):
        return clip.length
    
    
class LunarAltitudeMeasurement(Measurement):
    
    name = 'Lunar Altitude'
    
    def measure(self, clip):
        return _get_lunar_position(clip).altitude
    
    
def _get_lunar_position(clip):
    sun_moon = _get_sun_moon(clip)
    return sun_moon.get_lunar_position(clip.start_time)
    
    
class LunarAzimuthMeasurement(Measurement):
    
    name = 'Lunar Azimuth'
    
    def measure(self, clip):
        return _get_lunar_position(clip).azimuth
    
    
class LunarIlluminationMeasurement(Measurement):
    
    name = 'Lunar Illumination'
    
    def measure(self, clip):
        sun_moon = _get_sun_moon(clip)
        return sun_moon.get_lunar_illumination(clip.start_time)
    
    
class MicrophoneOutputNameMeasurement(Measurement):
    
    name = 'Microphone Output Name'
    
    def measure(self, clip):
        return clip.mic_output.name
    
    
class NauticalDawnMeasurement(_SolarEventTimeMeasurement):
    name = 'Nautical Dawn'


class NauticalDuskMeasurement(_SolarEventTimeMeasurement):
    name = 'Nautical Dusk'


class RecentClipCountMeasurement(Measurement):
    
    # This measurement assumes that clips of a given station and
    # detector are visited in order of increasing start time.
    
    name = 'Recent Clip Count'
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        annotation_name = settings.get('annotation_name', 'Classification')
        
        self._count_window_size = self._get_count_window_size(settings)
        
        self._included_classifications = \
            settings.get('included_classifications')
        
        self._excluded_classifications = \
            settings.get('excluded_classifications')
        
        self._lumped_classifications = \
            settings.get('lumped_classifications')
        
        self._clip_start_times = defaultdict(deque)
        
        self._annotation_info = \
            AnnotationInfo.objects.get(name=annotation_name)
    
    def _get_count_window_size(self, settings):
        window_size = settings.get('count_window_size', 60)
        return TimeDelta(seconds=window_size)

    def measure(self, clip):
        
        classification = \
            model_utils.get_clip_annotation_value(clip, self._annotation_info)
        
        if classification is None:
            return None
        
        classification_key = self._get_classification_key(classification)
        
        if classification_key is None:
            # clips of this classification not counted
            
            return None
        
        else:
            # clips of this classification counted
            
            # Get saved clip times.
            detector_name = model_utils.get_clip_detector_name(clip)
            key = (clip.station.name, detector_name, classification_key)
            clip_times = self._clip_start_times[key]
            
            # Discard saved clip times that precede count window.
            window_start_time = clip.start_time - self._count_window_size
            while len(clip_times) != 0 and clip_times[0] < window_start_time:
                clip_times.popleft()
            
            # Save current clip time.
            clip_times.append(clip.start_time)
            
            return len(clip_times)
    
    def _get_classification_key(self, classification):
        
        if self._included_classifications is not None:
            if not _matches(classification, self._included_classifications):
                return None
        
        if self._excluded_classifications is not None:
            if _matches(classification, self._excluded_classifications):
                return None
        
        if self._lumped_classifications is not None:
            for classifications in self._lumped_classifications:
                if _matches(classification, classifications):
                    return classifications[0]
        
        # If we get here, the classification is included but not lumped.
        return classification


def _matches(classification, classifications):
    
    for c in classifications:
        
        if c.endswith('*') and classification.startswith(c[:-1]):
            return True
        
        elif classification == c:
            return True
    
    # If we get here, `classification` did not match any of the
    # classifications in `classifications`.
    return False


class RecordingChannelNumberMeasurement(Measurement):
    
    name = 'Recording Channel Number'
    
    def measure(self, clip):
        return clip.channel_num


class RecordingDurationMeasurement(Measurement):
    
    name = 'Recording Duration'
    
    def measure(self, clip):
        return clip.recording.duration
        
        
class RecordingEndTimeMeasurement(Measurement):
    
    name = 'Recording End Time'
    
    def measure(self, clip):
        return clip.recording.end_time
    
    
class RecordingLengthMeasurement(Measurement):
    
    name = 'Recording Length'
    
    def measure(self, clip):
        return clip.recording.length
    
    

class RecordingStartTimeMeasurement(Measurement):
    
    name = 'Recording Start Time'
    
    def measure(self, clip):
        return clip.recording.start_time
    
    
_SOLAR_EVENT_NAMES = frozenset(SunMoon.SOLAR_EVENT_NAMES)


class _RelativeTimeMeasurement(Measurement):
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        self._reference_name = settings.get(
            'reference_time', 'Recording Start Time')
        
        if self._reference_name in _SOLAR_EVENT_NAMES:
            self._get_required_setting(settings, 'diurnal')
    
    def measure(self, clip):
        
        reference_time = self._get_reference_time(clip)
        
        if reference_time is None:
            return None
        
        else:
            clip_time = self._get_clip_time(clip)
            delta = clip_time - reference_time
            return delta.total_seconds()
    
    def _get_reference_time(self, clip):
        
        reference_name = self._reference_name
        
        if reference_name == 'Recording Start Time':
            return clip.recording.start_time
        
        elif reference_name == 'Recording End Time':
            return clip.recording.end_time
        
        elif reference_name == self._recording_file_start_time_reference_name:
            return self._get_recording_file_reference_time(clip, 'start')
            
        elif reference_name == self._recording_file_end_time_reference_name:
            return self._get_recording_file_reference_time(clip, 'end')
        
        else:
            return _get_solar_event_time(clip, reference_name, self._diurnal)
    
    def _get_recording_file_reference_time(self, clip, name):
        info = _get_recording_file_info(clip)
        if info is None:
            return None
        else:
            recording_file = info[0][self._recording_file_index]
            return getattr(recording_file, name + '_time')


class RelativeEndTimeMeasurement(_RelativeTimeMeasurement):
    
    name = 'Relative End Time'
    
    _recording_file_start_time_reference_name = \
        'Last Recording File Start Time'
    
    _recording_file_end_time_reference_name = \
        'Last Recording File End Time'
    
    _recording_file_index = -1
    
    def _get_clip_time(self, clip):
        return clip.end_time
    
    
class RelativeStartTimeMeasurement(_RelativeTimeMeasurement):
    
    name = 'Relative Start Time'
    
    _recording_file_start_time_reference_name = \
        'First Recording File Start Time'
    
    _recording_file_end_time_reference_name = \
        'First Recording File End Time'
    
    _recording_file_index = 0
    
    def _get_clip_time(self, clip):
        return clip.start_time
    
    
class SampleRateMeasurement(Measurement):
    
    name = 'Sample Rate'
    
    def measure(self, clip):
        return clip.sample_rate
    
    
class SensorNameMeasurement(Measurement):
    
    name = 'Sensor Name'
    
    def measure(self, clip):
        station_name = clip.station.name
        mic_name = clip.mic_output.device.name
        return f'{station_name} {mic_name}'


class SolarAltitudeMeasurement(Measurement):
    
    name = 'Solar Altitude'
    
    def measure(self, clip):
        return _get_solar_position(clip).altitude
    
    
def _get_solar_position(clip):
    sun_moon = _get_sun_moon(clip)
    return sun_moon.get_solar_position(clip.start_time)
    
    
class SolarAzimuthMeasurement(Measurement):
    
    name = 'Solar Azimuth'
    
    def measure(self, clip):
        return _get_solar_position(clip).azimuth
    
    
class SolarMidnightMeasurement(_SolarEventTimeMeasurement):
    name = 'Solar Midnight'
    
    
class SolarNoonMeasurement(_SolarEventTimeMeasurement):
    name = 'Solar Noon'
    
    
class SolarPeriodMeasurement(Measurement):
    
    name = 'Solar Period'
    
    def measure(self, clip):
        sun_moon = _get_sun_moon(clip)
        return sun_moon.get_solar_period_name(clip.start_time)


class StartIndexMeasurement(_IndexMeasurement):
    
    name = 'Start Index'
    
    _default_reference_index_name = 'Recording Start Index'
    
    _recording_file_start_index_reference_name = \
        'First Recording File Start Index'
    
    _recording_file_end_index_reference_name = \
        'First Recording File End Index'
    
    _recording_file_index = 0
    
    def _get_index(self, clip):
        return clip.start_index
    
    
class StartTimeMeasurement(Measurement):
    
    name = 'Start Time'
    
    def measure(self, clip):
        return clip.start_time
    
    
class StationNameMeasurement(Measurement):
    
    name = 'Station Name'
    
    def measure(self, clip):
        return clip.station.name
    
    
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
    FirstRecordingFileDurationMeasurement,
    FirstRecordingFileEndIndexMeasurement,
    FirstRecordingFileEndTimeMeasurement,
    FirstRecordingFileLengthMeasurement,
    FirstRecordingFileNameMeasurement,
    FirstRecordingFileNumberMeasurement,
    FirstRecordingFilePathMeasurement,
    FirstRecordingFileStartIndexMeasurement,
    FirstRecordingFileStartTimeMeasurement,
    IdMeasurement,
    LastRecordingFileDurationMeasurement,
    LastRecordingFileEndIndexMeasurement,
    LastRecordingFileEndTimeMeasurement,
    LastRecordingFileLengthMeasurement,
    LastRecordingFileNameMeasurement,
    LastRecordingFileNumberMeasurement,
    LastRecordingFilePathMeasurement,
    LastRecordingFileStartIndexMeasurement,
    LastRecordingFileStartTimeMeasurement,
    LengthMeasurement,
    LunarAltitudeMeasurement,
    LunarAzimuthMeasurement,
    LunarIlluminationMeasurement,
    MicrophoneOutputNameMeasurement,
    NauticalDawnMeasurement,
    NauticalDuskMeasurement,
    RecentClipCountMeasurement,
    RecordingChannelNumberMeasurement,
    RecordingDurationMeasurement,
    RecordingEndTimeMeasurement,
    RecordingLengthMeasurement,
    RecordingStartTimeMeasurement,
    RelativeEndTimeMeasurement,
    RelativeStartTimeMeasurement,
    SampleRateMeasurement,
    SensorNameMeasurement,
    SolarAltitudeMeasurement,
    SolarAzimuthMeasurement,
    SolarMidnightMeasurement,
    SolarNoonMeasurement,
    SolarPeriodMeasurement,
    StartIndexMeasurement,
    StartTimeMeasurement,
    StationNameMeasurement,
    SunriseMeasurement,
    SunsetMeasurement
])


_NO_VALUE_STRING = ''

_DEFAULT_DATE_FORMAT = '%Y-%m-%d'
_DEFAULT_TIME_FORMAT = '%H:%M:%S'
_DEFAULT_DATE_TIME_FORMAT = _DEFAULT_DATE_FORMAT + ' ' + _DEFAULT_TIME_FORMAT
_DEFAULT_DURATION_FORMAT = '%h:%M:%S'
_DEFAULT_RELATIVE_TIME_FORMAT = '%g%h:%M:%S'


class Formatter:
    
    def _get_required_setting(self, settings, name):
        try:
            return settings[name]
        except KeyError:
            raise CommandExecutionError(
                f'Formatter settings lack required "{name}" item.')
    
    def format(self, value, clip):
        if value is None:
            return None
        else:
            return self._format(value, clip)
        
        
class Calculator(Formatter):
    
    name = 'Calculator'
    
    def __init__(self, settings):
        self._code = self._get_required_setting(settings, 'code')
        self._calculator = Calculator_()
    
    def _format(self, value, clip):
        c = self._calculator
        try:
            c.clear()
            c.dict_stack.put('x', value)
            c.execute(self._code)
            return c.operand_stack.pop()
        except Exception as e:
            raise CommandExecutionError(
                f'Execution of calculator code "{self._code}" failed. '
                f'Calculator error message was: {str(e)}')
    
    
class DecimalFormatter(Formatter):
    
    name = 'Decimal Formatter'
    
    def __init__(self, settings=None):
        if settings is None:
            self._format_string = '{:f}'
        else:
            self._format_string = '{:' + settings.get('detail', '') + 'f}'
            
    def _format(self, x, clip):
        return self._format_string.format(x)


class _DateTimeFormatter(Formatter):
    
    def __init__(self, local, settings=None):
        
        self._local = local
        
        if settings is None:
            settings = {}
        
        self._formatter = self._get_formatter(settings)
        
        (self._rounding_enabled, self._rounding_increment,
            self._rounding_mode) = _get_rounding(
                settings, False, self._formatter.min_time_increment)
    
    def _get_formatter(self, settings):
        
        format_ = settings.get('format', _DEFAULT_DATE_TIME_FORMAT)
        
        # Try format string on test `DateTime` and raise an exception
        # if there's a problem.
        #
        # Commented the following out 2021-04-01 since it doesn't work
        # on Windows for extended format strings that include a specific
        # number of fractional digits, e.g. '%Y-%m-%d %H:%M:%S.%3f'.
        # Passing this string to `datetime.strftime` on macOS yields a
        # formatted date/time with ".%df" at the end, but raises a
        # `ValueError` exception on Windows.
        #
        # try:
        #     _TEST_DATE_TIME.strftime(format_)
        # except Exception as e:
        #     raise ValueError(
        #         f'Could not format test time with "{format_}". '
        #         f'Error message was: {str(e)}')
        
        return DateTimeFormatter(format_)
    
    def _format(self, dt, clip):
        
        # Round time if needed.
        if self._rounding_enabled:
            dt = time_utils.round_datetime(
                dt, self._rounding_increment, self._rounding_mode)
        
        # Get local time if needed.
        if self._local:
            time_zone = clip.station.tz
            dt = dt.astimezone(time_zone)
        
        # Get time string.
        return self._formatter.format(dt)


def _get_rounding(settings, default_enabled, default_increment):
    
    enabled = settings.get('rounding_enabled')
    increment = settings.get('rounding_increment')
    mode = settings.get('rounding_mode')

    if enabled is None:
        enabled = default_enabled or increment is not None or mode is not None
        
    if enabled:
        
        if increment is None:
            increment = default_increment
            if increment is None:
                increment = 1e-6
                
        if mode is None:
            mode = 'nearest'
    
    return enabled, increment, mode


class DurationFormatter(Formatter):

    name = 'Duration Formatter'
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        self._formatter = self._get_formatter(settings)
        
        (self._rounding_enabled, self._rounding_increment,
            self._rounding_mode) = _get_rounding(
                settings, True, self._formatter.min_time_increment)
    
    def _get_formatter(self, settings):
        format_ = settings.get('format', _DEFAULT_DURATION_FORMAT)
        return TimeDifferenceFormatter(format_)
    
    def _format(self, duration, clip):
        
        # Round duration if needed.
        if self._rounding_enabled:
            td = TimeDelta(seconds=duration)
            rounded_td = time_utils.round_timedelta(
                td, self._rounding_increment, self._rounding_mode)
            duration = rounded_td.total_seconds()
            
        return self._formatter.format(duration)


class LocalTimeFormatter(_DateTimeFormatter):
    
    name = 'Local Time Formatter'
    
    def __init__(self, settings=None):
        super().__init__(True, settings)
    
    
class LowerCaseFormatter(Formatter):
    
    name = 'Lower Case Formatter'
    
    def _format(self, value, clip):
        return value.lower()
    
    
class PercentFormatter(DecimalFormatter):
    
    name = 'Percent Formatter'
    
    def _format(self, x, clip):
        return super()._format(100 * x, clip)


class PrefixRemover(Formatter):
    
    name = 'Prefix Remover'
    
    def __init__(self, settings):
        self._prefix = self._get_required_setting(settings, 'prefix')
        self._prefix_length = len(self._prefix)
        
    def _format(self, value, clip):
        if not value.startswith(self._prefix):
            return None
        else:
            return value[self._prefix_length:]


class RelativeTimeFormatter(Formatter):

    name = 'Relative Time Formatter'
    
    def __init__(self, settings=None):
        
        if settings is None:
            settings = {}
            
        self._negation_enabled = settings.get('negation_enabled', False)
        self._formatter = self._get_formatter(settings)
        
        (self._rounding_enabled, self._rounding_increment,
            self._rounding_mode) = _get_rounding(
                settings, True, self._formatter.min_time_increment)
    
    def _get_formatter(self, settings):
        format_ = settings.get('format', _DEFAULT_RELATIVE_TIME_FORMAT)
        return TimeDifferenceFormatter(format_)
    
    def _format(self, relative_time, clip):
        
        # Negate relative time if needed.
        if self._negation_enabled:
            relative_time = -relative_time
        
        # Round relative time if needed.
        if self._rounding_enabled:
            td = TimeDelta(seconds=relative_time)
            rounded_td = time_utils.round_timedelta(
                td, self._rounding_increment, self._rounding_mode)
            relative_time = rounded_td.total_seconds()
            
        return self._formatter.format(relative_time)


class SolarDateFormatter(Formatter):
    
    name = 'Solar Date Formatter'
    
    def __init__(self, settings):
        self._diurnal = self._get_required_setting(settings, 'diurnal')
        self._format_string = settings.get('format', _DEFAULT_DATE_FORMAT)
    
    def _format(self, time, clip):
        
        # Get solar day or night.
        sun_moon = _get_sun_moon(clip)
        date = sun_moon.get_solar_date(time, self._diurnal)
        
        # Format date.
        return date.strftime(self._format_string)


class UpperCaseFormatter(Formatter):
    
    name = 'Upper Case Formatter'
    
    def _format(self, value, clip):
        return value.upper()
    
    
class UtcTimeFormatter(_DateTimeFormatter):
    
    name = 'UTC Time Formatter'
    
    def __init__(self, settings=None):
        super().__init__(False, settings)
            
    
class ValueMapper(Formatter):
    
    name = 'Value Mapper'
    
    def __init__(self, settings=None):
        if settings is None:
            self._mapping = {}
        else:
            self._mapping = settings.get('mapping', {})
            
    def _format(self, value, clip):
        return self._mapping.get(value, value)
    
    
_FORMATTER_CLASSES = dict((c.name, c) for c in [
    Calculator,
    DecimalFormatter,
    DurationFormatter,
    LocalTimeFormatter,
    LowerCaseFormatter,
    PercentFormatter,
    PrefixRemover,
    RelativeTimeFormatter,
    SolarDateFormatter,
    UpperCaseFormatter,
    UtcTimeFormatter,
    ValueMapper,
])
