import datetime
import os.path

import pytz

from vesper.mpg_ranch.recording_file_parser import RecordingFileParser
from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils
import vesper.util.time_utils as time_utils


DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)


class Station:
    
    def __init__(self, name):
        self.name = name
        
    def local_to_utc(self, dt):
        return to_utc(dt)
    
       
def create_station(name):
    return Station(name)


STATIONS = [
    Station('Floodplain'),
    Station('Ridge'),
    Station('Sheep Camp')
]


STATION_NAME_ALIASES = {
    'Floodplain': ['flood'],
    'Sheep Camp': ['sheep', 'sheepcamp']
}


class RecordingFileParserTests(TestCase):


    def test_parse_file(self):
        
        cases = [
                 
            ('FLOODPLAIN_20140820_210203.wav',
             'Floodplain', 1, 10, 24000, dt(2014, 8, 20, 21, 2, 3)),
                  
            ('FLOOD_20150601_200102.wav',
             'Floodplain', 2, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                   
            ('Ridge_20150601_200102.wav',
             'Ridge', 1, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                  
            ('Sheep Camp_20150601_200102.wav',
             'Sheep Camp', 1, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                   
            ('Sheep Camp_20150601_200102_comment_with_underscores.wav',
             'Sheep Camp', 1, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                   
            ('SHEEP_20150601_200102.wav',
             'Sheep Camp', 1, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                   
            ('SHEEPCAMP_20150601_200102.wav',
             'Sheep Camp', 1, 10, 22050, dt(2015, 6, 1, 20, 1, 2)),
                  
            ('ridge_042315_203600_101222.wav',
             'Ridge', 1, 10, 22050, dt(2015, 4, 23, 20, 36, 0)),
                   
            ('ridge_042315_203600_101222_comment.wav',
             'Ridge', 1, 10, 22050, dt(2015, 4, 23, 20, 36, 0)),
                 
        ]
        
        parser = RecordingFileParser(STATIONS, STATION_NAME_ALIASES)
        
        for (file_name, station_name, num_channels, length, sample_rate,
             start_time) in cases:
            
            file_path = os.path.join(DATA_DIR_PATH, file_name)
            info = parser.parse_file(file_path)
            
            self.assertEqual(info.station.name, station_name)
            self.assertIsNone(info.recorder)
            self.assertIsNone(info.recorder_channel_nums)
            self.assertEqual(info.num_channels, num_channels)
            self.assertIsNone(info.recorder_channel_nums)
            self.assertEqual(info.length, length)
            self.assertEqual(info.sample_rate, sample_rate)
            self.assertEqual(info.start_time, start_time)
            
            
    def test_parse_file_errors(self):
        
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
        
        parser = RecordingFileParser(STATIONS, STATION_NAME_ALIASES)
        
        for file_name in cases:
            file_path = os.path.join(DATA_DIR_PATH, file_name)
            self._assert_raises(ValueError, parser.parse_file, file_path)
            
            
def dt(*args):
    return to_utc(datetime.datetime(*args))


TIME_ZONE = pytz.timezone('US/Mountain')


def to_utc(dt):
    return time_utils.create_utc_datetime(
        dt.year, dt.month, dt.day, dt.hour,
        dt.minute, dt.second, dt.microsecond, TIME_ZONE)
