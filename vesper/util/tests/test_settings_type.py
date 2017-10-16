from pathlib import Path

from vesper.tests.test_case import TestCase
from vesper.util.settings import Settings
from vesper.util.settings_type import SettingsType
import vesper.tests.test_utils as test_utils


_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))
_SETTINGS_FILE_PATH = _DATA_DIR_PATH / 'Settings.yaml'


class SettingsTypeTests(TestCase):
    
    
    def test_init(self):
        
        cases = [
            ('One', Settings()),
            ('Two', Settings(x=1))
        ]
        
        for name, defaults in cases:
            t = SettingsType(name, defaults)
            self.assertEqual(t.name, name)
            self.assertEqual(t.defaults, defaults)
            
            
    def test_create_settings_from_dict(self):
        t = self._create_test_settings_type()
        s = t.create_settings_from_dict({'y': 3, 'z': 4})
        self._assert_created_settings(s)
        
        
    def _create_test_settings_type(self):
        defaults = Settings(x=1, y=2)
        return SettingsType('Bobo', defaults)
    
    
    def _assert_created_settings(self, settings):
        expected = Settings(x=1, y=3, z=4)
        self.assertEqual(settings, expected)


    def test_create_settings_from_yaml(self):
        t = self._create_test_settings_type()
        s = t.create_settings_from_yaml('{y: 3, z: 4}')
        self._assert_created_settings(s)
        
        
    def test_create_settings_from_yaml_file(self):
        t = self._create_test_settings_type()
        s = t.create_settings_from_yaml_file(_SETTINGS_FILE_PATH)
        self._assert_created_settings(s)
