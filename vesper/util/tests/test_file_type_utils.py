from pathlib import Path

from vesper.tests.test_case import TestCase
import vesper.tests.test_utils as test_utils
import vesper.util.file_type_utils as file_type_utils


DATA_DIR_PATH = test_utils.get_test_data_dir_path(__file__)

WAVE_TEST_CASES = (
    ('test.wav', True),
    ('test_uppercase.WAV', True),
    ('test.txt', False),
    ('test', False),
)

YAML_TEST_CASES = (
    ('test.yaml', True),
    ('test_uppercase.YAML', True),
    ('test.txt', False),
    ('test', False),
)

YAML_EXTENSIONS = ['yaml', 'YAML']


def create_dot_file_test_cases(cases):
    return tuple(('.' + n, x) for n, x in cases)


class FileTypeUtilsTests(TestCase):


    def test_is_wave_file(self):
        self._test_is_file_of_type(
            WAVE_TEST_CASES, file_type_utils.is_wave_file)
            
            
    def _test_is_file_of_type(self, cases, function):
        for file_name, expected in cases:
            path = Path(DATA_DIR_PATH, file_name)
            actual = function(path)
            self.assertEqual(actual, expected)
            
            
    def test_is_wave_file_for_dot_files(self):
        cases = create_dot_file_test_cases(WAVE_TEST_CASES)
        self._test_is_dot_file_of_type(cases, file_type_utils.is_wave_file)
        
        
    def _test_is_dot_file_of_type(self, cases, function):
        
        for file_name, has_extension in cases:
    
            path = Path(DATA_DIR_PATH, file_name)
    
            # omit `include_dot_files` argument
            actual = function(path)
            self.assertEqual(actual, False)
    
            # `include_dot_files` argument `False`
            actual = function(path, False)
            self.assertEqual(actual, False)
    
            # `include_dot_files` argument `True`
            actual = function(path, True)
            self.assertEqual(actual, has_extension)
            
            
    def test_is_yaml_file(self):
        self._test_is_file_of_type(
            YAML_TEST_CASES, file_type_utils.is_yaml_file)
        
        
    def test_is_yaml_file_for_dot_files(self):
        cases = create_dot_file_test_cases(YAML_TEST_CASES)
        self._test_is_dot_file_of_type(cases, file_type_utils.is_yaml_file)
        
        
    def test_nonexistent_file_error(self):
        path = Path(DATA_DIR_PATH, 'nonexistent_file')
        self.assert_raises(ValueError, file_type_utils.is_wave_file, path)
            
            
    def test_is_file_of_type(self):
        for file_name, expected in YAML_TEST_CASES:
            path = Path(DATA_DIR_PATH, file_name)
            actual = file_type_utils.is_file_of_type(path, YAML_EXTENSIONS)
            self.assertEqual(actual, expected)

    
    def test_is_file_of_type_for_dot_files(self):
    
        cases = create_dot_file_test_cases(YAML_TEST_CASES)
    
        function = file_type_utils.is_file_of_type
 
        for file_name, has_extension in cases:
    
            path = Path(DATA_DIR_PATH, file_name)
    
            # omit `include_dot_files` argument
            actual = function(path, YAML_EXTENSIONS)
            self.assertEqual(actual, False)
    
            # `include_dot_files` argument `False`
            actual = function(path, YAML_EXTENSIONS, False)
            self.assertEqual(actual, False)
    
            # `include_dot_files` argument `True`
            actual = function(path, YAML_EXTENSIONS, True)
            self.assertEqual(actual, has_extension)
