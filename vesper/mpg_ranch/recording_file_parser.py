"""Module containing class `RecordingFileParser`."""


import os.path
import re

from vesper.util.bunch import Bunch
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


_INPUT_FILE_NAME_RE_1 = \
    re.compile(
        r'^([^_]+)_(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)(_.+)?\.wav$')
    
_INPUT_FILE_NAME_RE_2 = \
    re.compile(
        r'^([^_]+)_(\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)_(\d{6})(_.+)?\.wav$')
    
    
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
        
        if station_name_aliases is None:
            station_name_aliases = {}
            
        self._stations = _create_stations_dict(stations, station_name_aliases)
        
        
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
            
            `station_recorder` - the `StationRecorder` of the recording.
            `num_channels` - the number of channels of the file.
            `length` - the length of the file in sample frames.
            `sample_rate` - the sample rate of the file in Hertz.
            `start_time` - the UTC start time of the file.
            `file_path` - the path of the file.
        """
        
        station, start_time = self._parse_file_name(file_path)
        
        num_channels, length, sample_rate = self._get_audio_file_info(file_path)
        
        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
        end_time = station.local_to_utc(end_time)
        station_recorder = \
            self._get_station_recorder(station, start_time, end_time)
            
        return Bunch(
            station_recorder=station_recorder,
            num_channels=num_channels,
            length=length,
            sample_rate=sample_rate,
            start_time=start_time,
            file_path=file_path)
        
    
    def _parse_file_name(self, file_path):
        
        file_name = os.path.basename(file_path)
        
        for parse_method in (self._parse_file_name_1, self._parse_file_name_2):
            
            try:
                station_name, year, month, day, hour, minute, second = \
                    parse_method(file_name)
                    
            except ValueError:
                continue
            
            else:
                # parse succeeded
            
                station = self._get_station(station_name)
                
                local_start_time = self._parse_file_name_date_time(
                    year, month, day, hour, minute, second)
        
                utc_start_time = station.local_to_utc(local_start_time)
                
                return station, utc_start_time
                
        # If we get here, the form of the file name was not recognized
        # by any of the parse methods.
        raise ValueError('File name is not of a recognized form.')
        
        
    def _parse_file_name_1(self, file_name):
        
        m = _INPUT_FILE_NAME_RE_1.match(file_name)
            
        if m is not None:
            return m.groups()[:-1]
        
        else:
            raise ValueError()
        

    def _parse_file_name_2(self, file_name):
        
        m = _INPUT_FILE_NAME_RE_2.match(file_name)
            
        if m is not None:
            
            station_name, month, day, year, hour, minute, second = \
                m.groups()[:-2]
                
            return (station_name, year, month, day, hour, minute, second)
        
        else:
            raise ValueError()
        

    def _get_station(self, station_name):
        try:
            return self._stations[station_name.lower()]
        except KeyError:
            raise ValueError(
                'Unrecognized station name "{}".'.format(station_name))


    def _parse_file_name_date_time(
            self, year, month, day, hour, minute, second):
        
        try:
            return time_utils.parse_date_time(
                year, month, day, hour, minute, second)
            
        except ValueError as e:
            raise ValueError(
                'Could not parse file name date and time: {}'.format(str(e)))
        

    def _get_station_recorder(self, station, start_time, end_time):
        
        station_recorders = station.get_station_devices(
            'Audio Recorder', start_time, end_time)
        
        if len(station_recorders) == 0:
            raise ValueError('Could not find recorder for file.')
        
        elif len(station_recorders) > 1:
            raise ValueError('Found more than one possible recorder for file.')
        
        else:
            return station_recorders[0]            
        
        
    def _get_audio_file_info(self, file_path):

        try:
            (num_channels, _, sample_rate, length, _) = \
                audio_file_utils.get_wave_file_info(file_path)
                
        except Exception as e:
            raise ValueError((
                'Attempt to read audio file metadata failed with message: '
                '{}').format(str(e)))
           
        return num_channels, length, sample_rate


def _create_stations_dict(stations, station_name_aliases):
    
    stations = dict((s.name, s) for s in stations)
    
    result = {}
    
    for station_name, aliases in station_name_aliases.items():
        
        try:
            station = stations[station_name]
        except KeyError:
            raise ValueError(
                'Unrecognized station name "{}".'.format(station_name))
            
        if isinstance(aliases, list):
            for alias in aliases:
                result[alias] = station
                    
        else:
            result[alias] = station
            
    # Always map the lower case version of each station name to that station.
    for station in stations.values():
        result[station.name.lower()] = station
            
    return result
