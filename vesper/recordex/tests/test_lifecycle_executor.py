import logging

from vesper.tests.test_case import TestCase
from vesper.recordex.lifecycle_executor import LifecycleExecutor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')

_logger = logging.getLogger(__name__)


class LifecycleExecutorTests(TestCase):


    def test_successful_lifecycle(self):

        lifecycle = (
            ('a', _logger, None),
            ('b', _logger, None))
        
        self._test(lifecycle, 'ab')


    def _test(self, lifecycle, expected_result):
        tester = _LifecycleTester()
        executor = LifecycleExecutor(tester, tester.name, lifecycle)
        executor.execute_lifecycle()
        self.assertEqual(tester.result, expected_result)


    def test_lifecycle_failure_with_no_logger_and_no_cleanup(self):

        lifecycle = (
            ('a', None, None),
            ('fail', None, None),
            ('b', None, None))
        
        self._test(lifecycle, 'a')


    def test_lifecycle_failure_with_no_logger_and_cleanup(self):

        lifecycle = (
            ('a', None, None),
            ('fail', None, 'c'),
            ('b', None, None),
            ('c', None, None))
        
        self._test(lifecycle, 'ac')

        
    def test_lifecycle_failure_with_logger_and_no_cleanup(self):

        lifecycle = (
            ('a', _logger, None),
            ('fail', _logger, None),
            ('b', _logger, None))
        
        self._test(lifecycle, 'a')


    def test_lifecycle_failure_with_logger_and_cleanup(self):

        lifecycle = (
            ('a', _logger, None),
            ('fail', _logger, 'c'),
            ('b', _logger, None),
            ('c', _logger, None))
        
        self._test(lifecycle, 'ac')


class _LifecycleTester:


    def __init__(self):
        self._result = ''


    @property
    def name(self):
        return '_LifecycleTester' 
    

    @property
    def result(self):
        return self._result
    

    def a(self):
        self._result += 'a'


    def b(self):
        self._result += 'b'


    def c(self):
        self._result += 'c'


    def fail(self):
        raise Exception('An error occurred.')
