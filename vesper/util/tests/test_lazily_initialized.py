from vesper.tests.test_case import TestCase
from vesper.util.lazily_initialized import LazilyInitialized


class LazilyInitializedTests(TestCase):


    def setUp(self):
        self.t = _Test()
        
        
    def test_property(self):
        self.assertEqual(self.t.x, 'x')
        
        
    def test_method(self):
        self.assertEqual(self.t.yy(), 'yy')
        
        
class _Test(LazilyInitialized):
    
    
    def _init(self):
        self._x = 'x'
        self._y = 'y'

        
    @property
    @LazilyInitialized.initter
    def x(self):
        return self._x
    
    
    @LazilyInitialized.initter
    def yy(self):
        return self._y + self._y
