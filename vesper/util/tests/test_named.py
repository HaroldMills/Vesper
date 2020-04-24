from vesper.tests.test_case import TestCase
from vesper.util.named import Named


class NamedTests(TestCase):


    def test_init(self):
        for name in ('One', 'Two'):
            named = Named(name)
            self.assertEqual(named.name, name)
        
        
    def test_eq(self):
        one_a = Named('One')
        one_b = Named('One')
        two = Named('Two')
        self.assertEqual(one_a, one_b)
        self.assertNotEqual(one_a, two)
