from vesper.tests.test_case import TestCase
from vesper.util.lru_cache import LruCache


class LruCacheTests(TestCase):


    def test_initializer(self):
        
        c = LruCache()
        self.assertIsNone(c.max_size)
        
        c = LruCache(10)
        self.assertEqual(c.max_size, 10)
    
    
    def test_get_and_set(self):
        
        c = LruCache(2)
        self._assert_cache(c, [])
        
        c['a'] = 0
        self._assert_cache(c, [('a', 0)])
        
        c['b'] = 1
        self._assert_cache(c, [('a', 0), ('b', 1)])
        
        c['c'] = 2
        self._assert_cache(c, [('b', 1), ('c', 2)])
        
        c['b'] = 3
        self._assert_cache(c, [('c', 2), ('b', 3)])
    
    
    def _assert_cache(self, c, expected_items):
        
        self.assertEqual(len(c), len(expected_items))
        
        actual_items = list(c.items())

        for i in range(len(expected_items)):
            self.assertEqual(actual_items[i], expected_items[i])
        
        for key, value in expected_items:
            self.assertEqual(c[key], value)
    
    
    def test_clear(self):
        
        c = LruCache(2)
        
        c['a'] = 0
        c['b'] = 1
        self._assert_cache(c, [('a', 0), ('b', 1)])
        
        c.clear()
        self._assert_cache(c, [])
