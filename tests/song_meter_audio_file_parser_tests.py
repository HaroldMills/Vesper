import datetime
import os.path

from mpg_ranch.song_meter_audio_file_parser import SongMeterAudioFileParser

from test_case import TestCase


_DATA_DIR_PATH = \
    os.path.join('data', 'song_meter_audio_file_parser Test Files')


class SongMeterSoundFileParserTests(TestCase):


    def test_get_file_info(self):
        
        cases = [
                 
            ('FLOODPLAIN_20140820_210203.wav',
             'Floodplain', ['NFC'], _dt(2014, 8, 20, 21, 2, 3), 10, 24000),
                  
            ('FLOOD_20150601_200102.wav',
             'Floodplain', ['NFC', '21c'], _dt(2015, 6, 1, 20, 1, 2), 10,
             22050),
                   
            ('Ridge_20150601_200102.wav',
             'Ridge', ['NFC'], _dt(2015, 6, 1, 20, 1, 2), 10, 22050),
                  
            ('Sheep Camp_20150601_200102.wav',
             'Sheep Camp', ['NFC'], _dt(2015, 6, 1, 20, 1, 2), 10, 22050),
                   
            ('Sheep Camp_20150601_200102_comment_with_underscores.wav',
             'Sheep Camp', ['NFC'], _dt(2015, 6, 1, 20, 1, 2), 10, 22050),
                   
            ('SHEEP_20150601_200102.wav',
             'Sheep Camp', ['NFC'], _dt(2015, 6, 1, 20, 1, 2), 10, 22050),
                   
            ('SHEEPCAMP_20150601_200102.wav',
             'Sheep Camp', ['NFC'], _dt(2015, 6, 1, 20, 1, 2), 10, 22050),
                  
            ('ridge_042315_203600_101222.wav',
             'Ridge', ['NFC'], _dt(2015, 4, 23, 20, 36, 0), 10, 22050),
                   
            ('ridge_042315_203600_101222_comment.wav',
             'Ridge', ['NFC'], _dt(2015, 4, 23, 20, 36, 0), 10, 22050),
                 
        ]
        
        parser = SongMeterAudioFileParser()
        
        for (file_name, station_name, mic_names, start_time, length,
             sample_rate) in cases:
            
            file_path = os.path.join(_DATA_DIR_PATH, file_name)
            info = parser.get_file_info(file_path)
            
            self.assertEqual(info.station_name, station_name)
            self.assertEqual(info.channel_microphone_names, mic_names)
            self.assertEqual(info.start_time, start_time)
            self.assertEqual(info.length, length)
            self.assertEqual(info.sample_rate, sample_rate)
            
            
    def test_get_file_info_errors(self):
        
        cases = [
                 
            # file names with unrecognized forms
            'bobo',
            'floot_20150601.wav',
            'flood_2010601_200102.wav',
            'flood_20150601_200102',
            'flood_20150601_200102.aif',
            
            # unrecognized station name
            'bobo_20150601_200102.wav',
            
            # bad date
            'flood_00000601_200102.wav',
            'flood_20150001_200102.wav',
            'flood_20150632_200102.wav',
            
            # bad time
            'flood_20150601_250102.wav',
            'flood_20150601_206002.wav',
            'flood_20150601_200160.wav',
            
        ]
        
        parser = SongMeterAudioFileParser()
        
        for file_name in cases:
            file_path = os.path.join(_DATA_DIR_PATH, file_name)
            self._assert_raises(ValueError, parser.get_file_info, file_path)
            
            
def _dt(*args):
    return datetime.datetime(*args)
