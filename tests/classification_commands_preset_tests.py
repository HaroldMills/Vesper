import vesper.util.classification_commands_preset as preset_module

from test_case import TestCase


class ClassificationCommandsPresetTests(TestCase):
    
    
    def test_parse_preset(self):
        
        cases = [
            ('c Call', {'c': ('Call', 'Selected')}),
            ('c Call Selected', {'c': ('Call', 'Selected')}),
            ('c Call Page', {'c': ('Call', 'Page')}),
            ('c Call All', {'c': ('Call', 'All')}),
            ('C COYE', {'C': ('COYE', 'Selected')}),
            ('Alt-c CMWA', {'Alt-c': ('CMWA', 'Selected')}),
            ('Alt-C CSWA', {'Alt-C': ('CSWA', 'Selected')})
        ]
        
        for text, expected in cases:
            commands = preset_module._parse_preset(text)
            self.assertEqual(commands, expected)
            
            
    def test_parse_preset_errors(self):
        
        cases = [
            'c',
            'c 2 3 4',
            'ca Call',
            'Alt-ca Call',
            '1 Call',
            'Ctrl-c Call',
            'c Call Bobo'
        ]
        
        for case in cases:
            self._assert_raises(ValueError, preset_module._parse_preset, case)
