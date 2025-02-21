from datetime import datetime as DateTime
import zoneinfo

from vesper.recorder.audio_file_writer import _AudioFileNamer
from vesper.tests.test_case import TestCase


class AudioFileNamerTests(TestCase):


    def test_get_file_name(self):
        namer = _AudioFileNamer('Ludlow', '.wav')
        zone_info = zoneinfo.ZoneInfo('UTC')
        file_start_time = DateTime(2025, 5, 1, 12, 34, 56, tzinfo=zone_info)
        name = namer.get_file_name(file_start_time)
        self.assertEqual(name, 'Ludlow_2025-05-01_12.34.56_Z.wav')
