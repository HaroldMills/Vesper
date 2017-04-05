from vesper.tests.test_case import TestCase
import vesper.util.case_utils as case_utils


class CaseUtilsTests(TestCase):
    
    
    def test_snake_to_camel(self):
        
        cases = (
            ('', ''),
            ('one', 'one'),
            ('one_two', 'oneTwo'),
            ('mixed_CASE_StrIng', 'mixedCaseString')
        )
        
        for s, expected in cases:
            result = case_utils.snake_to_camel(s)
            self.assertEqual(result, expected)
            
            
    def test_snake_keys_to_camel(self):
        
        cases = (
            (
                {'test': 0},
                {'test': 0}
            ), (
                {'HTML': 0},
                {'html': 0}
            ), (
                {'mixed_CASE_kEy': 0},
                {'mixedCaseKey': 0}
            ), (
                {'test_key': 'test_value'},
                {'testKey': 'test_value'}
            ), (
                {'key_one': 'value_one', 'key_two': 'value_two'},
                {'keyOne': 'value_one', 'keyTwo': 'value_two'}
            ), (
                {'key_one': {'key_two': 'value_two'}},
                {'keyOne': {'keyTwo': 'value_two'}}
            ), (
                {'key_one': ['string_one', {'key_two': 'value_two'}]},
                {'keyOne': ['string_one', {'keyTwo': 'value_two'}]}
            ), (
                [{'key_one': 1}, {'key_two': 2}],
                [{'keyOne': 1}, {'keyTwo': 2}]
            )
        )
        
        for d, expected in cases:
            result = case_utils.snake_keys_to_camel(d)
            self.assertEqual(result, expected)
        