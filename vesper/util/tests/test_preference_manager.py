from pathlib import Path

from vesper.tests.test_case import TestCase
from vesper.util.preference_manager import PreferenceManager
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))
_PREFERENCE_FILE_PATH = _DATA_DIR_PATH / 'Preferences.yaml'
_EMPTY_PREFERENCE_FILE_PATH = _DATA_DIR_PATH / 'Empty Preferences.yaml'
_NON_MAPPING_PREFERENCE_FILE_PATH = \
    _DATA_DIR_PATH / 'Non Mapping Preferences.yaml'
_MALFORMED_PREFERENCE_FILE_PATH = _DATA_DIR_PATH / 'Malformed Preferences.yaml'


class PreferenceManagerTests(TestCase):
    
    
    def test_get(self):
        
        preferences = _get_preferences(_PREFERENCE_FILE_PATH)

        cases = (
            ('one', 1),
            ('category_a.two', 2),
            ('category_a.three', 'three'),
            ('category_a.category_b.forty_five', 45),
            ('category_a.category_b.fifty six', 56),
            ('category_a.category_b', {'forty_five': 45, 'fifty six': 56})
        )
        
        for p in preferences:
            for name, value in cases:
                self.assertTrue(name in p)
                self.assertEqual(p[name], value)
                self.assertEqual(p.get(name), value)


    def test_get_of_nonexistent_preferences(self):
        
        preferences = _get_preferences(_PREFERENCE_FILE_PATH)

        cases = (
            'bobo',
            'category_a.bobo'
        )
        
        for p in preferences:
            for name in cases:
                self.assertFalse(name in p)
                self.assertRaises(KeyError, p.__getitem__, name)
                self.assertIsNone(p.get(name))
                self.assertEqual(p.get(name, 10), 10)
            
            
    def test_empty_preference_file(self):
        self._test_bad_preference_file(_EMPTY_PREFERENCE_FILE_PATH)


    def _test_bad_preference_file(self, file_path):
        preferences = _get_preferences(file_path)
        for p in preferences:
            self.assertEqual(len(p), 0)
        
        
    def test_malformed_preference_file(self):
        self._test_bad_preference_file(_MALFORMED_PREFERENCE_FILE_PATH)
        
        
    def test_non_mapping_preference_file(self):
        self._test_bad_preference_file(_NON_MAPPING_PREFERENCE_FILE_PATH)


    def test_nonexistent_preference_file(self):
        manager = PreferenceManager()
        manager.load_preferences_from_file('nonexistent')
        self.assertEqual(len(manager.preferences), 0)


def _get_preferences(file_path):

    # Create preferences from file.
    manager = PreferenceManager.create_for_file(file_path)
    preferences_a = manager.preferences

    # Create preferences from YAML.
    with open(file_path) as file_:
        yaml = file_.read()
    manager = PreferenceManager.create_for_yaml(yaml)
    preferences_b = manager.preferences

    return (preferences_a, preferences_b)
