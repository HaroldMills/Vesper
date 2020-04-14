from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch


class BunchTests(TestCase):


    def setUp(self):
        
        self.a = Bunch(one=1, two=2)
        self.b = Bunch(three=3, four=4)
        self.c = Bunch(self.a, self.b, five=5)
        
        
    def test_initializer(self):
        
        a = self.a
        self.assertEqual(a.one, 1)
        self.assertEqual(a.two, 2)
        
        b = self.b
        self.assertEqual(b.three, 3)
        self.assertEqual(b.four, 4)
        
        c = self.c
        self.assertEqual(c.one, 1)
        self.assertEqual(c.two, 2)
        self.assertEqual(c.three, 3)
        self.assertEqual(c.four, 4)
        self.assertEqual(c.five, 5)
        
        
    def test_eq(self):
        a = Bunch(one=1, two=2)
        self.assertEqual(a, self.a)
        self.assertNotEqual(a, self.b)
        
        
    def test_contains(self):
        self.assertIn('one', self.a)
        self.assertIn('two', self.a)
        self.assertNotIn('three', self.a)
        
        
    def test_iter(self):
        keys = sorted(k for k in self.a)
        self.assertEqual(keys, ['one', 'two'])
        
        
    def test_get(self):
        self.assertEqual(self.a.get('one'), 1)
        self.assertEqual(self.a.get('two'), 2)
        self.assertIsNone(self.a.get('three'))
        
        
    def test_get_defaults(self):
        self.assertEqual(self.a.get('seventeen'), None)
        self.assertEqual(self.a.get('seventeen', 17), 17)
