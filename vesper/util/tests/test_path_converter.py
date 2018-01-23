from pathlib import Path

from vesper.tests.test_case import TestCase
from vesper.util.path_converter import PathConverter
import vesper.tests.test_utils as test_utils


# TODO: Update `test_utils` to use `pathlib.Path`.
_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))


class PathConverterTests(TestCase):


    def test_init(self):
        
        cases = [
            (_DATA_DIR_PATH,),
            (Path('/one'), Path('/two'))
        ]
        
        for paths in cases:
            converter = PathConverter(paths)
            self.assertEqual(converter.root_dir_paths, paths)
        
        
    def test_init_errors(self):
        
        cases = [
            (),
            (Path('relative/path'),)
        ]
        
        for paths in cases:
            self._assert_raises(ValueError, PathConverter, paths)
        
        
    def test_single_root_dir_conversion(self):
        
        converter = PathConverter([_DATA_DIR_PATH])
        
        cases = [
            (Path(p), _DATA_DIR_PATH / p)
            for p in ['A/1.wav', 'A/2.wav', 'B/C/3.wav']
        ]
        
        self._test_conversion(converter, cases)
        
        
    def _test_conversion(self, converter, cases):
        
        for rel_path, abs_path in cases:
            
            actual = converter.absolutize(rel_path)
            self.assertEqual(actual, abs_path)
            
            root_dir_path, actual = converter.relativize(abs_path)
            self.assertEqual(actual, rel_path)
            self.assertEqual(root_dir_path / actual, abs_path)
            
            
    def test_double_root_dir_conversion(self):
        
        converter = PathConverter([
            _DATA_DIR_PATH / 'A',
            _DATA_DIR_PATH / 'B'
        ])
        
        cases = [
            (Path('1.wav'), _DATA_DIR_PATH / 'A/1.wav'),
            (Path('2.wav'), _DATA_DIR_PATH / 'A/2.wav'),
            (Path('C/3.wav'), _DATA_DIR_PATH / 'B/C/3.wav')
        ]
        
        self._test_conversion(converter, cases)
        
        
    def test_absolutize_errors(self):
        
        converter = PathConverter([_DATA_DIR_PATH])
        
        cases = [
            _DATA_DIR_PATH,              # already absolute
            Path('A/nonexistent.wav')    # nonexistent
        ]
        
        for path in cases:
            self._assert_raises(ValueError, converter.absolutize, path)
        
        
    def test_relativize_errors(self):
        
        converter = PathConverter([_DATA_DIR_PATH])
        
        cases = [
            Path('relative.wav'),         # already relative
            Path(_DATA_DIR_PATH.parent)   # not within root dir
        ]
        
        for path in cases:
            self._assert_raises(ValueError, converter.relativize, path)