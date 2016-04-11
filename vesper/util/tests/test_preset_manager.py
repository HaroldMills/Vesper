import os

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
    
    type_name = 'A'
    
    def __init__(self, name, data):
        super(A, self).__init__(name)
        self.data = data.strip()
        
          
class B(_Preset):
    
    type_name = 'B'
    
    def __init__(self, name, data):
        super(B, self).__init__(name)
        self.data = yaml.load(data)
        
        
_DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)


class PresetManagerTests(TestCase):
    
    
    def setUp(self):
        self.manager = PresetManager(_DATA_DIR_PATH, (A, B))

        
    def test_preset_types(self):
        type_names = [t.type_name for t in self.manager.preset_types]
        self.assertEqual(type_names, ['A', 'B'])
        
        
    def test_get_presets(self):
        
        expected = {
            
            'A': (
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
                 }),
                    
            'B': ((B('1', '1'), B('2', '2')), {}),
            'X': ((), {})
            
        }
        
        for type_name, expected_data in expected.items():
            preset_data = self.manager.get_presets(type_name)
            self.assertEqual(preset_data, expected_data)
            
            
    def test_flatten_preset_data(self):
        
        cases = [
                 
            ('A', ((('1',), A('1', 'one')),
                   (('2',), A('2', 'two')),
                   (('x', 'y', '3'), A('3', 'three')),
                   (('x', 'z', '4'), A('4', 'four')))),
                 
            ('B', ((('1',), B('1', '1')),
                   (('2',), B('2', '2')))),
                 
            ('X', ())
            
        ]
        
        for type_name, expected_data in cases:
            preset_data = self.manager.get_presets(type_name)
            flattened_data = self.manager.flatten_preset_data(preset_data)
            self.assertEqual(flattened_data, expected_data)
