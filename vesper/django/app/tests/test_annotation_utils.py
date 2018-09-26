import vesper.django.app.annotation_utils as utils
from vesper.tests.test_case import TestCase


class AnnotationUtilsTests(TestCase):
    
    
    def test_create_string_annotation_values_regexp(self):
        
        cases = [
            
            (
                [],
                
                [('', False),
                 ('Call', False),
                 ('Call.AMRE', False),
                 ('CallAMRE', False),
                 ('Noise', False),
                 ('Nocturnal', False)]
             
            ), (
              
                ['*'],
                
                [('', True),
                 ('Call', True),
                 ('Call.AMRE', True),
                 ('CallAMRE', True),
                 ('Noise', True),
                 ('Nocturnal', True)]

            ), (
                
                ['Call.*', 'Noise'],
                
                [('', False),
                 ('Call', False),
                 ('Call.AMRE', True),
                 ('CallAMRE', False),
                 ('Noise', True),
                 ('Nocturnal', False)]
             
            ), (
                
                ['Call*', 'Noise'],
                
                [('', False),
                 ('Call', True),
                 ('Call.AMRE', True),
                 ('CallAMRE', False),
                 ('Noise', True),
                 ('Nocturnal', False)]
             
            )
                 
        ]
        
        for values, examples in cases:
            
            regexp = utils.create_string_annotation_values_regexp(values)
            
            for s, expected in examples:
                
                result = regexp.match(s)
                
                if expected:
                    self.assertNotEqual(result, None)
                else:
                    self.assertEqual(result, None)
