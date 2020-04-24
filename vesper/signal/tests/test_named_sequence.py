from vesper.tests.test_case import TestCase
from vesper.util.named import Named

from vesper.signal.named_sequence import NamedSequence


class _Item(Named):
    
    
    def __init__(self, name, value):
        super().__init__(name)
        self.value = value
        
        
    def __eq__(self, other):
        return isinstance(other, _Item) and \
            self.name == other.name and \
            self.value == other.value
        
        
class NamedSequenceTests(TestCase):
    
    
    def test_init(self):
        s = NamedSequence()
        self.assertEqual(len(s), 0)
        self.assertEqual(s.names, ())
        
        
    def test_eq(self):
        
        one = _Item('one', 1)
        two = _Item('two', 2)
        three = _Item('three', 3)
        
        s = NamedSequence((one, two))
        
        t = NamedSequence((one, two))
        self.assertTrue(s == t)
        
        t = NamedSequence((one, three))
        self.assertFalse(s == t)


    def test(self):
        
        one = _Item('one', 1)
        two = _Item('two', 2)
        three = _Item('three', 3)
        s = NamedSequence((one, two))
        
        # indexing with integers
        self.assertEqual(s[0], one)
        self.assertEqual(s[1], two)
        self._assert_raises(IndexError, s.__getitem__, 2)
        
        # indexing with names
        self.assertEqual(s['one'], one)
        self.assertEqual(s['two'], two)
        self._assert_raises(IndexError, s.__getitem__, 'three')
        
        # `names` attribute
        self.assertEqual(s.names, ('one', 'two'))
        
        # containment
        self.assertTrue(one in s)
        self.assertTrue(two in s)
        self.assertFalse(three in s)
        self.assertFalse(0 in s)
        
        # iteration
        items = [i for i in s]
        self.assertEqual(items, [one, two])
        
        # reversed
        items = [i for i in reversed(s)]
        self.assertEqual(items, [two, one])
        
        # index
        self.assertEqual(s.index(one), 0)
        self.assertEqual(s.index(two), 1)
        self._assert_raises(ValueError, s.index, three)
        
        # count
        self.assertEqual(s.count(one), 1)
        self.assertEqual(s.count(two), 1)
        self.assertEqual(s.count(three), 0)
