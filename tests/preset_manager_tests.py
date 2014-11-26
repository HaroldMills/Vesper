from __future__ import print_function

import json
import os
import unittest

from nfc.util.preset import Preset
from nfc.util.preset_manager import PresetManager


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
        self.data = json.loads(data)
        
        
class PresetManagerTests(unittest.TestCase):
    
    
    def setUp(self):
        path = os.path.dirname(__file__)
        path = os.path.join(path, 'data', 'Test Presets')
        self.manager = PresetManager(path, (A, B))

        
    def test_preset_types(self):
        type_names = [t.type_name for t in self.manager.preset_types]
        self.assertEqual(type_names, ['A', 'B'])
        
        
    def test_get_presets(self):
        
        expected = {
            
            'A': (
                [A('1', 'one'), A('2', 'two')],
                {'x': (
                    [],
                    {'y': (
                        [A('3', 'three')],
                        {}),
                     'z': (
                        [A('4', 'four')],
                        {})
                     })
                 }),
                    
            'B': ([B('1', '1'), B('2', '2')], {}),
            'X': ([], {})
            
        }
        
        for type_name, expected_data in expected.iteritems():
            preset_data = self.manager.get_presets(type_name)
            self.assertEqual(preset_data, expected_data)
