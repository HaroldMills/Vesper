import os.path

from vesper.util.vesper_path_utils import get_path

from test_case import TestCase


class VesperPathUtilsTests(TestCase):


    def test_get_path(self):
        
        vesper_home = _get_vesper_home_dir_path()
        self.assertEqual(get_path('Vesper Home'), vesper_home)
        
        user_home = os.path.expanduser('~')
        self.assertEqual(get_path('User Home'), user_home)
        
        # We do not test `get_path('App Data')` here since to do so
        # would more or less require duplicating here the code we
        # are testing.
        
        
    def test_get_path_errors(self):
        self._assert_raises(KeyError, get_path, 'Bobo')


def _get_vesper_home_dir_path():
    d = os.path.dirname
    return d(d(__file__))