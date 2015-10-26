"""Module containing class `SongMeterAudioFileParser`."""


import os.path
import re

import yaml

from vesper.util.bunch import Bunch
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.util.vesper_path_utils as vesper_path_utils


_INPUT_FILE_NAME_RE_1 = \
    re.compile(
        r'^([^_]+)_(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)(_.+)?\.wav$')
    
_INPUT_FILE_NAME_RE_2 = \
    re.compile(
        r'^([^_]+)_(\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)_(\d{6})(_.+)?\.wav$')
    
    
def _get_station_name_translations(prefs):
    
    # TODO: We assume here that if the YAML parses the result has a
    # certain structure, but it might not. We need a general way to
    # validate the structure of parsed YAML. Perhaps we could use
    # declarative YAML descriptions of the required structure, or
    # perhaps somebody has already implemented something like this?
    
    aliases = prefs.get('station_name_aliases', {})
    return _invert_aliases_dict(aliases)


def _invert_aliases_dict(aliases):
    
    translations = {}
    
    for translation, a in aliases.iteritems():
        
        if isinstance(a, list):
            
            for alias in a:
                
                if alias in translations:
                    
                    raise ValueError(
                        ('Alias "{:s}" specified for both "{:s}" '
                         'and "{:s}".').format(
                            str(alias), str(translations[alias]),
                            str(translation)))
                    
                else:
                    translations[alias] = translation
                    
        else:
            translations[a] = translation
            
    return translations
            
        
def _get_channel_microphone_names(prefs, file_path):
    
    # TODO: We assume here that if the YAML parses the result has a
    # certain structure, but it might not. We need a general way to
    # validate the structure of parsed YAML. Perhaps we could use
    # declarative YAML descriptions of the required structure, or
    # perhaps somebody has already implemented something like this?
    
    key = 'channel_microphone_names'
    try:
        return prefs[key]
    except KeyError:
        raise ValueError(
            'Required preference "{}" is missing from file "{}".'.format(
                key, file_path))
        

class SongMeterAudioFileParser(object):
    
    
    """
    Parses MPG Ranch Song Meter audio files.
    
    This class provides information about an MPG Ranch Song Meter audio
    file. Some of the information, including the station name and the
    recording start time, is obtained by parsing the audio file name.
    The information obtained from the file name may optionally be
    transformed according to information provided in the preferences
    file:
    
        MPG Ranch/Song Meter Audio File Parser.yaml
        
    located within the user's preferences directory. For example, a
    station name alias that appears in a file name can be mapped to
    the "official" archive station name, and channel microphone names
    can be determined from a table that specifies the microphones
    used at various stations during various date ranges.
    
    The rest of the information, including the length of the recording
    in sample frames and the recording sample rate, is obtained from
    within the audio file.
    """
    
    
    def __init__(self):
        
        super(SongMeterAudioFileParser, self).__init__()
        
        self._get_preferences()
        
        
    def _get_preferences(self):
        
        app_data_dir_path = vesper_path_utils.get_path('App Data')
        file_path = os.path.join(
            app_data_dir_path, 'Preferences', 'MPG Ranch',
            'Song Meter Audio File Parser.yaml')
        
        try:
            text = os_utils.read_file(file_path)
        except Exception as e:
            raise ValueError((
                'Could not read preferences file "{}". Error message '
                'was: {}').format(file_path, str(e)))
            
        try:
            prefs = yaml.load(text)
        except Exception as e:
            raise ValueError((
                'Could not parse YAML from preferences file "{}". '
                'Error message was: {}').format(file_path, str(e)))
            
        self._station_name_translations = _get_station_name_translations(prefs)
        
        self._channel_microphone_names = \
            _get_channel_microphone_names(prefs, file_path)
        
        
    def get_file_info(self, file_path):
    
        station_name, start_time = self._parse_file_name(file_path)
        
        mic_names = self._get_channel_microphone_names(
            station_name, start_time)
        
        num_channels, sample_rate, length = \
            self._get_audio_file_info(file_path)
        
        if num_channels != len(mic_names):
            raise ValueError((
                'Number of file channels ({:d}) does not match number of '
                'channel microphone names ({:d}).').format(
                    num_channels, len(mic_names)))
            
        return Bunch(
            station_name=station_name,
            channel_microphone_names=mic_names,
            start_time=start_time,
            length=length,
            sample_rate=sample_rate)
        
    
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
            
                station_name = self._translate_station_name(station_name)
                
                start_time = self._parse_file_name_date_time(
                    year, month, day, hour, minute, second)
        
                return station_name, start_time
                
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
        

    def _translate_station_name(self, station_name):
        name = station_name.lower()
        return self._station_name_translations.get(name, name)


    def _parse_file_name_date_time(
            self, year, month, day, hour, minute, second):
        
        try:
            return time_utils.parse_date_time(
                year, month, day, hour, minute, second)
        except ValueError as e:
            raise ValueError(
                'Could not parse file name date and time: {:s}'.format(str(e)))
        

    def _get_channel_microphone_names(self, station_name, start_time):
        
        mic_dicts = self._channel_microphone_names.get(station_name)
        
        if mic_dicts is None:
            raise ValueError(
                'Unrecognized station name "{:s}".'.format(station_name))
            
        night = start_time.date()
        
        for d in mic_dicts:
            if d['start_night'] <= night and night <= d['end_night']:
                return d['microphones']
            
        # If we get here, the microphone names dictionary does not
        # have microphone names for the specified station and night.
        night = night.strftime('%Y-%m-%d')
        raise ValueError((
            'No channel microphone names found for station "{:s}" and '
            'night "{:s}".').format(station_name, night))
    
    
    def _get_audio_file_info(self, file_path):

        try:
            (num_channels, _, sample_rate, length, _) = \
                audio_file_utils.get_wave_file_info(file_path)
        except Exception as e:
            raise ValueError((
                'Attempt to read audio file metadata failed with message: '
                '{:s}').format(str(e)))
           
        return num_channels, sample_rate, length

