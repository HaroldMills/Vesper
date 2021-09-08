from vesper.tests.test_case import TestCase
import vesper.util.matching_utils as matching_utils


class MatchingUtilsTests(TestCase):


    def test(self):
        
        cases = [
            
            # zero-length sequences
            (([], []), []),
            (([(0, 1)], []), []),
            (([], [(0, 1)]), []),
        
            # single-element, identical sequences
            (([(0, 1)], [(0, 1)]), [(0, 0)]),
            
            # single-element, intersecting but not identical sequences
            (([(0, 1)], [(.5, 1.5)]), [(0, 0)]),
            (([(0, 1)], [(.5, 1.5)], .5), [(0, 0)]),
            (([(0, 1)], [(.5, 1.5)], .500001), []),
 
            # single-element, non-intersecting sequences
            (([(0, 1)], [(1, 2)]), []),
            
            # source interval that matches more than one target interval
            (([(0, 3)], [(0, 1), (2, 3)]), [(0, 0), (0, 1)]),
            
            # target interval that matches more than one source interval
            # (Note that first source interval matches instead of second
            # one, even though absolute size of intersection of second
            # one with target interval is larger, since it's the
            # relative size of the intersection that matters.)
            (([(0, 1), (2, 4)], [(0, 4)]), [(0, 0)]),
            
            # intersections within source and target interval sequences
            (([(0, 3), (1, 4), (2, 5)], [(1, 3), (2, 4), (3, 5)]),
             [(0, 0), (1, 1), (2, 2)]),
            
            # longer sequences
            (([(0, 4), (5, 9), (10, 14), (15, 19)],
              [(1, 2), (3, 4), (5, 6), (7, 8), (8, 12), (13, 14), (14, 15),
               (16, 20), (21, 22)]),
             [(0, 0), (0, 1), (1, 2), (1, 3), (2, 4), (2, 5), (3, 7)]),
            
        ]
                   
        for args, expected in cases:
            actual = matching_utils.match_intervals(*args)
            self.assertEqual(actual, expected)
