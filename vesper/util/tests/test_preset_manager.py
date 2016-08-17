import yaml

from vesper.tests.test_case import TestCase
from vesper.util.preset import Preset
from vesper.util.preset_manager import PresetManager
import vesper.tests.test_utils as test_utils


class _Preset(Preset):
    
    def __eq__(self, other):
        return type(other) == type(self) and \
            self.name == other.name and \
            self.data == other.data

    
class A(_Preset):
    
    extension_name = 'A'
    
    def __init__(self, name, data):
        data = data.strip()
        super().__init__(name, data)
        
          
class B(_Preset):
    
    extension_name = 'B'
    
    def __init__(self, name, data):
        data = yaml.load(data)
        super().__init__(name, data)
        
        
_DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)


class PresetManagerTests(TestCase):
    
    
    def setUp(self):
        self.manager = PresetManager((A, B), _DATA_DIR_PATH)

        
    def test_preset_types(self):
        type_names = [t.extension_name for t in self.manager.preset_types]
        self.assertEqual(type_names, ['A', 'B'])
        
        
    def test_get_presets(self):
        
        cases = (
            
            ('A', (
                (A('1', 'one'), A('2', 'two')),
                {'x': (
                    (),
                    {'y': (
                        (A('3', 'three'),),
                        {}),
                     'z': (
                        (A('4', 'four'),),
                        {})
                     })
                 })),
                    
            ('B', ((B('1', '1'), B('2', '2')), {})),
            ('X', ((), {}))
            
        )
        
        for type_name, expected in cases:
            presets = self.manager.get_presets(type_name)
            self.assertEqual(presets, expected)


    def test_get_flattened_presets(self):
        
        cases = (
                 
            ('A', ((('1',), A('1', 'one')),
                   (('2',), A('2', 'two')),
                   (('x', 'y', '3'), A('3', 'three')),
                   (('x', 'z', '4'), A('4', 'four')))),
                 
            ('B', ((('1',), B('1', '1')),
                   (('2',), B('2', '2')))),
                 
            ('X', ())
            
        )
        
        for type_name, expected in cases:
            presets = self.manager.get_flattened_presets(type_name)
            self.assertEqual(presets, expected)
            
            
    def test_get_preset(self):
        
        cases = [
                 
            ('A', '1', A('1', 'one')),
            ('A', ('2',), A('2', 'two')),
            ('A', ('x', 'y', '3'), A('3', 'three')),
            ('A', ('x', 'z', '4'), A('4', 'four')),
            
            ('B', '1', B('1', '1')),
            ('B', '2', B('2', '2')),
            
            ('A', 'bobo', None),
            ('A', ('bobo',), None),
            ('X', 'bobo', None)
            
        ]
        
        for type_name, path, expected in cases:
            preset = self.manager.get_preset(type_name, path)
            self.assertEqual(preset, expected)
            