import vesper.django.app.annotation_utils as utils
from vesper.tests.test_case import TestCase


_DEFAULT_SPECS = [
    utils.UNANNOTATED_CLIPS,
    utils.ALL_CLIPS,
    utils.ANNOTATED_CLIPS
]


class AnnotationUtilsTests(TestCase):
    
    
    def test_get_string_annotation_value_specs(self):
        
        cases = [
            
            ([], _DEFAULT_SPECS),
            
            (
                ['Call.AMRE', 'Call.COYE', 'Noise'],
                
                 _DEFAULT_SPECS + [
                     'Call', 'Call*', 'Call.*', 'Call.AMRE', 'Call.COYE',
                     'Noise']
             )
                 
        ]
        
        for values, expected in cases:
            specs = utils.get_string_annotation_value_specs(values)
            self.assertEqual(specs, expected)
