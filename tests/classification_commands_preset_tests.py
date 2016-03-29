import vesper.util.classification_commands_preset as preset_module

from test_case import TestCase


class ClassificationCommandsPresetTests(TestCase):
    
    
    def test_parse_preset(self):
          
        cases = [
            ('".": {action: None}', {'.': 'Selected'}),
            ('c: Call', {'c': 'Selected'}),
            ('c: {class: Call, scope: Selected}', {'c': 'Selected'}),
            ('c: {class: Call, scope: Page}', {'c': 'Page'}),
            ('c: {class: Call, scope: All}', {'c': 'All'}),
            ('c: {classifier: "NFC Coarse Clip Classifier", scope: Page}',
             {'c': 'Page'})
        ]
          
        for text, expected in cases:
            commands = preset_module._parse_preset(text)
            commands = dict(
                (name, scope) for name, (_, scope) in commands.iteritems())
            self.assertEqual(commands, expected)
            
            
    def test_parse_preset_errors(self):
         
        cases = [
            'bobo',
            'cc: Call',
            '~: Call',
            '-: Call',
            'Ctrl-c: Call',
            'c: []',
            'c: {action: Bobo}',
            'c: {class: Call, scope: Bobo}',
            'c: {class: Call, classifier: Bobo}',
            'c: {action: Classify}'
        ]
         
        for case in cases:
            self._assert_raises(ValueError, preset_module._parse_preset, case)
