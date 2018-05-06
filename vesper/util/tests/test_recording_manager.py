from pathlib import Path

from vesper.tests.test_case import TestCase
from vesper.util.recording_manager import RecordingManager
import vesper.tests.test_utils as test_utils


# TODO: Update `test_utils` to use `pathlib.Path`.
_DATA_DIR_PATH = Path(test_utils.get_test_data_dir_path(__file__))

_ARCHIVE_DIR_PATH = Path('/Archive')


class RecordingManagerTests(TestCase):


    def test_init_archive_path(self):
        
        cases = [
            _ARCHIVE_DIR_PATH,
            Path(_ARCHIVE_DIR_PATH)
        ]
        
        for case in cases:
            expected = Path(_ARCHIVE_DIR_PATH)
            manager = RecordingManager(case, [])
            self.assertEqual(manager.archive_dir_path, expected)
        
        
    def test_init_archive_path_errors(self):
        self._assert_raises(ValueError, RecordingManager, 'Archive', [])
        
        
    def test_init_directory_paths(self):
        
        cases = [
            
            ((), ()),
            ((_DATA_DIR_PATH,), (_DATA_DIR_PATH,)),
            (('/one', '/two'), ('/one', '/two')),
             
            # relative paths
            ((Path('relative/path'),), ('/Archive/relative/path',)),
            (('/bobo', 'relative/path', '/bobo2'),
             ('/bobo', '/Archive/relative/path', '/bobo2')),
             
            # duplicate paths
            (('/bobo', '/bobo'), ('/bobo',)),
            (('/Bobo', '/bobo'), ('/Bobo',))
            
        ]
        
        for paths, expected in cases:
            expected = tuple([_get_path_object(p) for p in expected])
            manager = _create_recording_manager(paths)
            self.assertEqual(manager.recording_dir_paths, expected)
        
        
    def test_zero_recording_dir_conversion(self):
        manager = _create_recording_manager([])
        self._test_conversion_errors(manager)
         
         
    def _test_conversion_errors(self, manager):
         
        # relative to absolute
        self._assert_raises(
            ValueError, manager.get_absolute_recording_file_path, Path('bobo'))
         
        # absolute to relative
        cases = [
            '/bobo',    # already absolute
            'bobo'      # nonexistent
        ]
        for case in cases:
            self._assert_raises(
                ValueError, manager.get_relative_recording_file_path, case)
          
          
    def test_single_recording_dir_conversion(self):
          
        manager = _create_recording_manager([_DATA_DIR_PATH])
          
        cases = [
            (Path(p), _DATA_DIR_PATH / p)
            for p in ['A/1.wav', 'A/2.wav', 'B/C/3.wav']
        ]
          
        self._test_conversion(manager, cases)
         
        self._test_conversion_errors(manager)
         
          
    def _test_conversion(self, manager, cases):
          
        for rel_path, abs_path in cases:
              
            actual = manager.get_absolute_recording_file_path(rel_path)
            self.assertEqual(actual, abs_path)
              
            recording_dir_path, actual = \
                manager.get_relative_recording_file_path(abs_path)
            self.assertEqual(actual, rel_path)
            self.assertEqual(recording_dir_path / actual, abs_path)
              
              
    def test_double_recording_dir_conversion(self):
          
        manager = _create_recording_manager([
            _DATA_DIR_PATH / 'A',
            _DATA_DIR_PATH / 'B'
        ])
          
        cases = [
            (Path('1.wav'), _DATA_DIR_PATH / 'A/1.wav'),
            (Path('2.wav'), _DATA_DIR_PATH / 'A/2.wav'),
            (Path('C/3.wav'), _DATA_DIR_PATH / 'B/C/3.wav')
        ]
          
        self._test_conversion(manager, cases)
         
        self._test_conversion_errors(manager)
         

def _get_path_object(p):
    return p if isinstance(p, Path) else Path(p)


def _create_recording_manager(recording_dir_paths):
    return RecordingManager(_ARCHIVE_DIR_PATH, recording_dir_paths)
