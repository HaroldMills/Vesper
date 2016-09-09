from vesper.tests.test_case import TestCase
import vesper.util.text_utils as text_utils


class TextUtilsTests(TestCase):
    
    
    def test_create_string_item_list(self):
        
        cases = (
            ([], ''),
            (['one'], 'one'),
            (['one', 'two'], 'one and two'),
            (['one', 'two', 'three'], 'one, two, and three'),
            (['one', 'two', 'three', 'four'], 'one, two, three, and four'),
            ([1, 2, 3], '1, 2, and 3')
        )
        
        for items, expected in cases:
            result = text_utils.create_string_item_list(items)
            self.assertEqual(result, expected)
        