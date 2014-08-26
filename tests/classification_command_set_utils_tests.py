import nfc.util.classification_command_set_utils as utils

from test_case import TestCase


class ClassificationCommandSetUtilsTests(TestCase):
    
    
    def test_parse_command_set(self):
        
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
            commands = utils.parse_command_set(text)
            self.assertEqual(commands, expected)
            
            
    def test_parse_command_set_errors(self):
        
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
            self._assert_raises(ValueError, utils.parse_command_set, case)
