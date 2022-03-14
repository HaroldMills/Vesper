from collections import defaultdict
from pathlib import Path

from vesper.tests.test_case import TestCase
from vesper.util.preset import Preset
from vesper.util.preset_manager import PresetManager
import vesper.tests.test_utils as test_utils
import vesper.util.yaml_utils as yaml_utils


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
        data = yaml_utils.load(data)
        super().__init__(name, data)
        
        
# Preset type for which there are no presets, and for which there is
# no preset type directory.
class C(A):
    extension_name = 'C'


PRESET_DIR_PATH = test_utils.get_test_data_dir_path(__file__)

PRESET_TYPES = (A, B, C)


def create_preset(path, data):
    cls = globals()[path[0]]
    return cls(path, data)


PRESETS = tuple(create_preset(*d) for d in (
    
    (('A', '1'), 'one'),
    (('A', '2'), 'two'),
    (('A', 'x', 'y', '3'), 'three'),
    (('A', 'x', 'z', '4'), 'four'),
    
    (('B', '1'), '1'),
    (('B', '2'), '2'),
    
))


def get_preset_tuples():
    
    # Build mapping from preset type name to list of presets.
    preset_lists = defaultdict(list)
    for p in PRESETS:
        preset_lists[p.path[0]].append(p)
        
    # Convert lists to tuples.
    preset_tuples = dict(
        (type_name, tuple(presets))
        for type_name, presets in preset_lists.items())
    
    # Add empty tuple for preset type with no preset type directory.
    preset_tuples['C'] = ()
    
    return preset_tuples
    
    
PRESET_TUPLES = get_preset_tuples()
    
    
class PresetManagerTests(TestCase):
    
    
    def setUp(self):
        self.manager = PresetManager(PRESET_DIR_PATH, PRESET_TYPES)

        
    def test_preset_dir_path(self):
        self.assertEqual(self.manager.preset_dir_path, Path(PRESET_DIR_PATH))
    
    
    def test_preset_types(self):
        self.assertEqual(self.manager.preset_types, PRESET_TYPES)
    
    
    def test_get_presets(self):
        for type_name, expected_presets in PRESET_TUPLES.items():
            actual_presets = self.manager.get_presets(type_name)
            self.assertEqual(actual_presets, expected_presets)
    
    
    def test_get_presets_errors(self):
        self._assert_raises(ValueError, self.manager.get_presets, 'X')
        
        
    def test_get_preset(self):
        for expected_preset in PRESETS:
            actual_preset = self.manager.get_preset(expected_preset.path)
            self.assertEqual(actual_preset, expected_preset)
            
            
    def test_get_nonexistent_preset(self):
        preset = self.manager.get_preset(('A', 'Bobo'))
        self.assertIsNone(preset)
        
        
    def test_get_preset_errors(self):
        
        # Unrecognized preset type.
        self._assert_raises(ValueError, self.manager.get_preset, ('X', 'Bobo'))
        
        
    def test_unload_presets(self):
        
        manager = self.manager
        
        # Load some presets.
        self.test_get_presets()
        
        # Unload all presets.
        manager.unload_presets()
        
        # Check that no presets are loaded.
        self.assertEqual(manager._loaded_preset_types, ())
        self.assertEqual(manager._loaded_presets, ())
        
        # Load presets again.
        self.test_get_presets()
        
        # Unload presets of just type A.
        manager.unload_presets('A')
        
        # Check that presets of type B and C are loaded, but none of type A.
        self.assertEqual(manager._loaded_preset_types, (B, C))
        presets = manager._loaded_presets
        self.assertEqual(len(presets), 2)
        for preset in presets:
            self.assertEqual(preset.path[0], 'B')
            