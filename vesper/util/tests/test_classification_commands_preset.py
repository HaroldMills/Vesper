from vesper.tests.test_case import TestCase
import vesper.util.classification_commands_preset as preset_module


class ClassificationCommandsPresetTests(TestCase):
    
    
    def test_normalize_name(self):
        
        cases = [
            ('a', 'A'),
            ('A', 'Shift+A'),
            ('+', '+'),
            ('1', '1'),
            ('!', '!'),
            ('Alt+1', 'Alt+1'),
            ('Alt+!', 'Alt+!'),
            ('Alt+n', 'Alt+N'),
            ('Alt+N', 'Alt+Shift+N')
        ]
        
        for name, expected in cases:
            result = preset_module._normalize_name(name)
            self.assertEqual(result, expected)
            
            
    def test_parse_preset(self):
          
        cases = [
            ('".": {action: None}', {'.': 'Selected'}),
            ('c: Call', {'C': 'Selected'}),
            ('c: {class: Call, scope: Selected}', {'C': 'Selected'}),
            ('c: {class: Call, scope: Page}', {'C': 'Page'}),
            ('c: {class: Call, scope: All}', {'C': 'All'}),
            ('c: {classifier: "NFC Coarse Clip Classifier", scope: Page}',
             {'C': 'Page'})
        ]
          
        for text, expected in cases:
            commands = preset_module._parse_preset(text)
            commands = dict(
                (name, scope) for name, (_, scope) in commands.items())
            self.assertEqual(commands, expected)
            
            
    def test_parse_preset_errors(self):
         
        cases = [
            'bobo',
            '"": Call',
            'cc: Call',
            '~: Call',              # tilde is nil in YAML
            'Ctrl+c: Call',
            'c: []',
            'c: {action: Bobo}',
            'c: {class: Call, scope: Bobo}',
            'c: {class: Call, classifier: Bobo}',
            'c: {action: Classify}'
        ]
         
        for case in cases:
            self._assert_raises(ValueError, preset_module._parse_preset, case)
