import os.path
import re

import yaml

from vesper.util.bunch import Bunch
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.time_utils as time_utils


_INPUT_FILE_NAME_RE_1 = \
    re.compile(
        r'^([^_]+)_(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)(_.+)?\.wav$')
    
_INPUT_FILE_NAME_RE_2 = \
    re.compile(
        r'^([^_]+)_(\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)_(\d{6})(_.+)?\.wav$')
    
    
_STATION_NAME_ALIASES = '''
   Floodplain: [floodplain, flood]
   Ridge: ridge
   Sheep Camp: [sheep camp, sheep, sheepcamp]
'''

_MICROPHONE_NAME_ALIASES = '''
    21c: c
    NFC: n
    SMX-II: s
'''

_CHANNEL_MICROPHONE_NAMES = '''
    
    Floodplain:
    
        - start_night: 2014-08-01
          end_night: 2014-10-01
          microphones: [NFC]
          
        - start_night: 2015-04-22
          end_night: 2015-06-11
          microphones: [NFC, 21c]
          
    Ridge:
    
        - start_night: 2014-08-02
          end_night: 2014-10-21
          microphones: [NFC]
          
        - start_night: 2015-04-23
          end_night: 2015-06-10
          microphones: [NFC]
          
    Sheep Camp:
    
        - start_night: 2014-04-11
          end_night: 2014-04-17
          microphones: [SMX-II]
          
        - start_night: 2014-04-18
          end_night: 2014-06-08
          microphones: [SMX-II, NFC]
          
        - start_night: 2015-04-22
          end_night: 2015-06-10
          microphones: [NFC]
          
'''


def _parse_station_name_aliases(aliases_yaml):
    
    # TODO: We assume here that if the YAML parses the result has a
    # certain structure, but it might not. We need a general way to
    # validate the structure of parsed YAML. Perhaps we could use
    # declarative YAML descriptions of the required structure, or
    # perhaps somebody has already implemented something like this?
    
    aliases = _parse_yaml(aliases_yaml, 'station name aliases')
    return _invert_aliases_dict(aliases)


def _parse_yaml(s, description):
    try:
        return yaml.load(s)
    except ValueError as e:
        raise ValueError((
            'Could not parse {:s} YAML. '
            'Error message was: {:s}').format(description, str(e)))

        
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
            
        
def _parse_channel_microphone_names(names_yaml):
    
    # TODO: We assume here that if the YAML parses the result has a
    # certain structure, but it might not. We need a general way to
    # validate the structure of parsed YAML. Perhaps we could use
    # declarative YAML descriptions of the required structure, or
    # perhaps somebody has already implemented something like this?
    
    # `names` is a dictionary mapping station names to lists of
    # microphone name dictionaries. Each microphone name dictionary
    # contains "start_night", "end_night", and "microphones" keys.
    return _parse_yaml(names_yaml, 'station microphone names')
        
    
class SongMeterAudioFileParser(object):
    
    
    def __init__(self):
        
        super(SongMeterAudioFileParser, self).__init__()
        
        self._station_name_translations = \
            _parse_station_name_aliases(_STATION_NAME_ALIASES)
        
        self._channel_microphone_names = \
            _parse_channel_microphone_names(_CHANNEL_MICROPHONE_NAMES)
        
        
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

