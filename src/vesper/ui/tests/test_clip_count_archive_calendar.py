import unittest

import vesper.ui.clip_count_archive_calendar as calendar


class ClipCountArchiveCalendarTests(unittest.TestCase):


    def test_get_calendar_spans(self):
        
        cases = [
                 
            # no months
            ([], []),
            
            # one partition
            ([1], [(1, 1)]),
            ([1, 2], [(1, 2)]),
            ([1, 2, 3], [(1, 3)]),
            ([12, 13], [(12, 13)]),
            
            # more than one partition
            ([1, 2, 5], [(1, 2), (5, 5)]),
            ([1, 2, 5, 6, 7, 12, 13, 14], [(1, 2), (5, 7), (12, 14)]),
            
            # filled-in gaps
            ([1, 2, 4], [(1, 4)]),
            ([1, 3, 5, 7, 12, 14], [(1, 7), (12, 14)])
            
        ]
        
        for months, expected in cases:
            pairs = [_to_pair(m) for m in months]
            expected = [(_to_month_num(s), _to_month_num(e))
                        for s, e in expected]
            spans = calendar._get_calendar_spans(pairs)
            self.assertEqual(spans, expected)


def _to_pair(n):
    year = 2014 + (n - 1) // 12
    month = (n - 1) % 12 + 1
    return (year, month)


def _to_month_num(n):
    return calendar._to_month_num(*_to_pair(n))
