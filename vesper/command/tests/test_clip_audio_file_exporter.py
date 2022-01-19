from vesper.tests.test_case import TestCase
import vesper.command.clip_audio_file_exporter as clip_audio_file_exporter


class ClipAudioFileExporterTests(TestCase):
        
        
    def test_parse_time_interval_preset_aux(self):
        
        parse = clip_audio_file_exporter._parse_time_interval_preset_aux

        data = {}
        result = parse(data)
        self.assertEqual(result.left_padding, 0)
