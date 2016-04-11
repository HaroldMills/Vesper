import unittest

import vesper.util.text_utils as test_utils


class TextUtilsTests(unittest.TestCase):
    
    
    def test_format_number(self):
        
        cases = [
                 
            # integers
            (0, '0'),
            (1, '1.0'),
            (9, '9.0'),
            (10, '10'),
            (99, '99'),
            (1234, '1234'),
            
            # floats
            (.0000000001, '0.00000000010'),
            (.00000000011, '0.00000000011'),
            (.123, '0.12'),
            (.125, '0.12'),
            (.12500001, '0.13'),
            (1.23, '1.2'),
            (1.25, '1.2'),
            (1.2500001, '1.3'),
            (9.49999, '9.5'),
            (9.5, '10'),
            (10.1, '10'),
            (1234.56, '1235')
            
        ]
        
        for x, expected in cases:
            result = test_utils.format_number(x)
            self.assertEqual(result, expected)
            