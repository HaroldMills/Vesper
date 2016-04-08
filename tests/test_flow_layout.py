import unittest

from vesper.ui.flow_layout import FlowLayout


class FlowLayoutTests(unittest.TestCase):
    
    
    def setUp(self):
        self.sizes = (1, 1.5, 1, 2, 1.5, 1.25, 3, 6, 1, 1.5, 6, .75)
        self.layout = FlowLayout(5, .1)
        
        
    def test_empty_layout(self):
        result = self.layout.lay_out_items([])
        self.assertEqual(result, [])
        
        
    def test_full_layout(self):
        result = self.layout.lay_out_items(self.sizes)
        expected_result = \
            [(0, 3), (3, 2), (5, 2), (7, 1), (8, 2), (10, 1), (11, 1)]
        self.assertEqual(result, expected_result)
        
        
    def test_partial_initial_layout(self):
        result = self.layout.lay_out_items(self.sizes, max_num_rows=2)
        expected_result = [(0, 3), (3, 2)]
        self.assertEqual(result, expected_result)
        
        
    def testPartialNoninitialLayout(self):
        result = self.layout.lay_out_items(
                     self.sizes, start_item_num=1, max_num_rows=2)
        expected_result = [(1, 3), (4, 2)]
        self.assertEqual(result, expected_result)
