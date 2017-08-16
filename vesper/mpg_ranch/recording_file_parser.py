"""Module containing class `RecordingFileParser`."""


import os.path
import re

import pytz

from vesper.util.bunch import Bunch
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.time_utils as time_utils


# TODO: Support recording file parser extensions.
# TODO: Support specification of file name formats via YAML.
# TODO: Should recording file parser find recorder as well as station?


class _FileNameParser:
    
    
    def __init__(self, stations, station_name_aliases=None):
        
        """
        Initializes this parser for the specified stations and aliases.
        
        :Parameters:
        
            stations : collection of `Station` objects
                the stations whose recording files will be parsed.
                
            station_name_aliases: mapping from `str` to `str`
                mapping from station names to station name aliases.
                
                The station name aliases appear in file names and will
                be translated by the parser into regular station names.
                The capitalization of aliases is inconsequential since
                the parser will compare them to the station names that
                appear in file names only after both are converted to
                lower case.
        """
        
        if station_name_aliases is None:
            station_name_aliases = {}
            
        self._stations = _create_stations_dict(stations, station_name_aliases)


    def parse_file_name(self, file_name):
        
        (station_name, recorder_channel_nums,
         year, month, day, hour, minute, second) = \
            self._get_file_name_fields(file_name)
            
        station = self._get_station(station_name)
        
        naive_start_time = _get_file_name_date_time(
            year, month, day, hour, minute, second)

        utc_start_time = self._get_utc_start_time(naive_start_time, station)
        
        return station, recorder_channel_nums, utc_start_time
            

    def _get_file_name_fields(self, file_name):
        raise NotImplementedError()
    
    
    def _get_station(self, station_name):
        try:
            return self._stations[station_name.lower()]
        except KeyError:
            raise ValueError(
                'Unrecognized station name "{}".'.format(station_name))
            
            
    def _get_utc_start_time(self, naive_start_time, station):
        raise NotImplementedError()


def _get_file_name_fields_with_regex(file_name, regex):
    
    """
    Parses a file name using a regular expression.
    
    This method assumes that `self._re` is a compiled regular
    expression that, when 
    """
    
    m = regex.match(file_name)
        
    if m is not None:
        return _get_file_name_fields_aux(m.group)
    
    else:
        raise ValueError()


def _get_file_name_fields_aux(g, recorder_channel_nums=None):
    
    return (
        g('station_name'),
        recorder_channel_nums,
        g('year'), g('month'), g('day'),
        g('hour'), g('minute'), g('second'))
    

def _create_stations_dict(stations, station_name_aliases):
    
    stations = dict((s.name, s) for s in stations)
    
    result = {}
    
    for station_name, aliases in station_name_aliases.items():
        
        try:
            station = stations[station_name]
            
        except KeyError:
            # unrecognized station name
            
            # Here we ignore unrecognized station names in station name
            # alias dictionaries. The proper time to warn about them
            # would be when the presets that specify the dictionaries
            # are parsed, rather than here.
            pass
            
        else:
            
            if isinstance(aliases, list):
                for alias in aliases:
                    result[alias] = station
                        
            else:
                result[alias] = station
            
    # Always map the lower case version of each station name to that station.
    for station in stations.values():
        result[station.name.lower()] = station
            
    return result

        
def _get_file_name_date_time(year, month, day, hour, minute, second):
    
    try:
        return time_utils.parse_date_time(
            year, month, day, hour, minute, second)
        
    except ValueError as e:
        raise ValueError(
            'Could not parse file name date and time: {}'.format(str(e)))
        

class _VesperRecorderFileNameParser(_FileNameParser):
    
    
    _REGEX = re.compile(
        r'^'
        r'(?P<station_name>[^_]+)'
        r'_'
        r'(?P<year>\d\d\d\d)-(?P<month>\d\d)-(?P<day>\d\d)'
        r'_'
        r'(?P<hour>\d\d)\.(?P<minute>\d\d)\.(?P<second>\d\d)_Z'
        r'\.wav'
        r'$')
    
    
    def _get_file_name_fields(self, file_name):
        return _get_file_name_fields_with_regex(file_name, self._REGEX)

            
    def _get_utc_start_time(self, naive_start_time, station):
        return pytz.utc.localize(naive_start_time)

    
class _SongMeterFileNameParser(_FileNameParser):
    
    
    _REGEX = re.compile(
        r'^'
        r'(?P<station_name>[^_]+)'
        r'_'
        r'(?P<channel_nums>_0__|_1__|0\+1_|0\+1_0_|0\+1_1_)?'
        r'(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)'
        r'_'
        r'(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d)'
        r'\.wav'
        r'$')
    
    
    _CHANNEL_NUMS = {
        '_0__': (0,),
        '_1__': (1,),
        '0+1_': (0, 1),
        '0+1_0_': (0,),
        '0+1_1_': (1,),
        None: None
    }
    
    
    def _get_file_name_fields(self, file_name):

        m = self._REGEX.match(file_name)
            
        if m is not None:
            g = m.group
            channel_nums = self._CHANNEL_NUMS[g('channel_nums')]
            return _get_file_name_fields_aux(g, channel_nums)
        
        else:
            raise ValueError()


    def _get_utc_start_time(self, naive_start_time, station):
        return station.local_to_utc(naive_start_time)
    
    
class _MpgRanchFileNameParser0(_FileNameParser):
    
    
    _REGEX = re.compile(
        r'^'
        r'(?P<station_name>[^_]+)'
        r'_'
        r'(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)'
        r'_'
        r'(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d)'
        r'(_.+)'      # trailing comment
        r'\.wav'
        r'$')

    
    def _get_file_name_fields(self, file_name):
        return _get_file_name_fields_with_regex(file_name, self._REGEX)

            
    def _get_utc_start_time(self, naive_start_time, station):
        return station.local_to_utc(naive_start_time)
    
        
class _MpgRanchFileNameParser1(_FileNameParser):
    
    
    _REGEX = re.compile(
        r'^'
        r'(?P<station_name>[^_]+)'
        r'_'
        r'(?P<month>\d\d)(?P<day>\d\d)(?P<year>\d\d)'
        r'_'
        r'(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d)'
        r'_'
        r'(\d{6})'    # six mystery digits (hhmmss recording duration?)
        r'(_.+)?'     # optional trailing comment
        r'\.wav'
        r'$')

    
    def _get_file_name_fields(self, file_name):
        return _get_file_name_fields_with_regex(file_name, self._REGEX)


    def _get_utc_start_time(self, naive_start_time, station):
        return station.local_to_utc(naive_start_time)


class _EasyHiQRecorderFileNameParser(_FileNameParser):
    
    
    _REGEX = re.compile(
        r'^'
        r'(?P<month>\d\d?)-(?P<day>\d\d?)-(?P<year>\d\d\d\d)'
        r'_'
        r'(?P<hour>\d\d?);(?P<minute>\d\d);(?P<second>\d\d)'
        r'_'
        r'(?P<period>AM|PM)'
        r'\.wav'
        r'$')
    
    
    def _get_file_name_fields(self, file_name):
        
        parts = file_name.rsplit(' ', 1)
        
        if len(parts) != 2:
            raise ValueError()
        
        station_name, rest = parts
        
        m = self._REGEX.match(rest)
        
        if m is None:
            raise ValueError()
        
        g = m.group
        
        hour = self._get_hour(g('hour'), g('period'))
            
        return(
            station_name, None,
            g('year'), g('month'), g('day'),
            hour, g('minute'), g('second'))
        
        
    def _get_hour(self, hour, period):
        
        hour = int(hour)
        
        # Check that hour is in [0, 11].
        if hour >= 12:
            raise ValueError()
        
        # Convert hour to 24-hour time.
        if period == 'PM':
            hour += 12
            
        return str(hour)
            
            
    def _get_utc_start_time(self, naive_start_time, station):
        return station.local_to_utc(naive_start_time)

    
class RecordingFileParser:
    
    """
    Parses recording files.
    
    This class provides information about an audio file that contains
    part or all of a recording. Some of the information, including the
    station and the recording start time, is obtained by parsing the
    recording file name. The station name obtained from the file name
    may optionally be transformed according to a specified Station Name
    Aliases preset.
    
    The rest of the information, including the length of the recording
    in sample frames and the recording sample rate, is obtained from
    within the recording file.
    """
    
    
    extension_name = 'MPG Ranch Recording File Parser'
    
    
    def __init__(self, stations, station_name_aliases=None):
        
        """
        Initializes this parser for the specified stations and aliases.
        
        :Parameters:
        
            stations : collection of `Station` objects
                the stations whose recording files will be parsed.
                
            station_name_aliases: mapping from `str` to `str`
                mapping from station names to station name aliases.
                
                The station name aliases appear in file names and will
                be translated by the parser into regular station names.
                The capitalization of aliases is inconsequential since
                the parser will compare them to the station names that
                appear in file names only after both are converted to
                lower case.
        """
        
        self._file_name_parsers = (
            _VesperRecorderFileNameParser(stations, station_name_aliases),
            _SongMeterFileNameParser(stations, station_name_aliases),
            _MpgRanchFileNameParser0(stations, station_name_aliases),
            _MpgRanchFileNameParser1(stations, station_name_aliases),
            _EasyHiQRecorderFileNameParser(stations, station_name_aliases)
        )
        
        
    def parse_file(self, file_path):
    
        """
        Parses the specified recording file for recording information.
        
        Some information is obtained from the file path, while other
        information is obtained from within the file.
        
        :Parameters:
            file_path : `str`
                the path of the file to parse.
                
        :Returns:
            a `Bunch` with the following attributes:
            
            `station` - the `Station` of the recording.
            `recorder` - the `Recorder` of the recording, or `None` if unknown.
            `recorder_channel_nums` - sequence of recorder channel numbers
                indexed by recording channel number, or `None` if unknown.
            `num_channels` - the number of channels of the file.
            `length` - the length of the file in sample frames.
            `sample_rate` - the sample rate of the file in Hertz.
            `start_time` - the UTC start time of the file.
            `path` - the path of the file.
        """
        
        station, recorder_channel_nums, start_time = \
            self._parse_file_name(file_path)
        
        num_channels, length, sample_rate = self._get_audio_file_info(file_path)
        
        return Bunch(
            station=station,
            recorder=None,
            recorder_channel_nums=recorder_channel_nums,
            num_channels=num_channels,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            path=file_path)
        
    
    def _parse_file_name(self, file_path):
        
        file_name = os.path.basename(file_path)
        
        for parser in self._file_name_parsers:
            
            try:
                return parser.parse_file_name(file_name)
                    
            except ValueError:
                continue
                
        # If we get here, the file name could not be parsed by any of
        # the file name parsers.
        raise ValueError('Could not parse file name.')
        
        
    def _get_audio_file_info(self, file_path):

        try:
            info = audio_file_utils.get_wave_file_info(file_path)
                
        except Exception as e:
            raise ValueError((
                'Attempt to read audio file metadata failed with message: '
                '{}').format(str(e)))
           
        return info.num_channels, info.length, info.sample_rate
