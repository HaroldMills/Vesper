from pathlib import Path

import yaml

from vesper.tests.test_case import TestCase
from vesper.util.settings import Settings
import vesper.tests.test_utils as test_utils
import vesper.util.os_utils as os_utils


_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))
_EMPTY_SETTINGS_FILE_PATH = _DATA_DIR_PATH / 'Empty Settings.yaml'
_COMMENTED_OUT_SETTINGS_FILE_PATH = \
    _DATA_DIR_PATH / 'Commented-out Settings.yaml'
_SETTINGS_FILE_PATH = _DATA_DIR_PATH / 'Settings.yaml'
_NON_ARRAY_SETTINGS_FILE_PATH = _DATA_DIR_PATH / 'Non-array Settings.yaml'
_MALFORMED_SETTINGS_FILE_PATH = _DATA_DIR_PATH / 'Malformed Settings.yaml'


class SettingsTests(TestCase):
    
    
    def test_init(self):
        
        s = Settings()
        self.assertEqual(len(s.__dict__), 0)
        
        s = Settings(x=1, y=2)
        self.assertEqual(s.x, 1)
        self.assertEqual(s.y, 2)
        
        defaults = Settings(x=1, y=2)
        s = Settings(defaults, x=3)
        self.assertEqual(s.x, 3)
        self.assertEqual(s.y, 2)
        
        
    def test_create_from_dict(self):
        contents = os_utils.read_file(_SETTINGS_FILE_PATH)
        d = yaml.load(contents)
        settings = Settings.create_from_dict(d)
        self._check_settings(settings)
        
        
    def _check_settings(self, s):
        self.assertEqual(s.null_setting, None)
        self.assertEqual(s.boolean_setting, True)
        self.assertEqual(s.integer_setting, 10)
        self.assertEqual(s.float_setting, 1.5)
        self.assertEqual(s.string_setting, 'Hello, world!')
        self.assertEqual(s.list_setting, [1, 2, 3])
        self.assertEqual(s.object_setting.one, 1)
        self.assertEqual(s.object_setting.two, 2)

    
    def test_create_from_empty_yaml(self):
        settings = Settings.create_from_yaml('')
        self._check_empty_settings(settings)
        
        
    def _check_empty_settings(self, settings):
        self.assertEqual(len(settings.__dict__), 0)
        
        
    def test_create_from_commented_out_yaml(self):
        settings = Settings.create_from_yaml('#')
        self._check_empty_settings(settings)
        
        
    def test_create_from_yaml(self):
        contents = os_utils.read_file(_SETTINGS_FILE_PATH)
        settings = Settings.create_from_yaml(contents)
        self._check_settings(settings)

        
    def test_create_from_empty_yaml_file(self):
        settings = Settings.create_from_yaml_file(_EMPTY_SETTINGS_FILE_PATH)
        self._check_empty_settings(settings)
        
        
    def test_create_from_commented_out_yaml_file(self):
        settings = Settings.create_from_yaml_file(
            _COMMENTED_OUT_SETTINGS_FILE_PATH)
        self._check_empty_settings(settings)
        
        
    def test_create_from_yaml_file(self):
        settings = Settings.create_from_yaml_file(_SETTINGS_FILE_PATH)
        self._check_settings(settings)
        
        
    def test_non_dict_settings_error(self):
        self._assert_raises(TypeError, Settings.create_from_dict, 'bobo')
        
        
    def test_non_array_settings_error(self):
        self._assert_raises(
            ValueError, Settings.create_from_yaml_file,
            _NON_ARRAY_SETTINGS_FILE_PATH)
        
        
    def test_malformed_settings_error(self):
        self._assert_raises(
            ValueError, Settings.create_from_yaml_file,
            _MALFORMED_SETTINGS_FILE_PATH)
