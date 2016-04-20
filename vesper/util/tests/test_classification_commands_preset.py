from vesper.tests.test_case import TestCase
from vesper.util.classification_commands_preset \
    import ClassificationCommandsPreset
import vesper.util.classification_commands_preset as preset_module


class ClassificationCommandsPresetTests(TestCase):
    
    
    def test_parse_command_name(self):
         
        cases = [
            ('a', ([], 'a')),
            ('A', ([], 'A')),
            ('+', ([], '+')),
            ('1', ([], '1')),
            ('!', ([], '!')),
            ('Alt+1', (['Alt'], '1')),
            ('Alt+!', (['Alt'], '!')),
            ('Alt+n', (['Alt'], 'n')),
            ('Alt+N', (['Alt'], 'N')),
            ('Alt++', (['Alt'], '+'))
        ]
         
        for name, expected in cases:
            result = ClassificationCommandsPreset.parse_command_name(name)
            self.assertEqual(result, expected)
            
            
    def test_parse_command_name_errors(self):
        
        cases = [
            None,
            5,
            {},
            '',
            '++',
            '+++',
            'bobo',
            'Ctrl-n',
            'Ctrl+n'
        ]
        
        parse = ClassificationCommandsPreset.parse_command_name
        
        for case in cases:
            self._assert_raises(ValueError, parse, case)
            
        
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
                (name, scope) for name, (_, scope) in commands.items())
            self.assertEqual(commands, expected)
            
            
    def test_parse_preset_errors(self):
         
        cases = [
            '~: Call',              # tilde is nil in YAML
            '5: Call',
            '{}: Call'
            'bobo',
            '"": Call',
            'cc: Call',
            'Ctrl+c: Call',
            'c: []',
            'c: {action: Bobo}',
            'c: {class: Call, scope: Bobo}',
            'c: {class: Call, classifier: Bobo}',
            'c: {action: Classify}'
        ]
         
        for case in cases:
            self._assert_raises(ValueError, preset_module._parse_preset, case)
