import datetime

from vesper.tests.test_case import TestCase
from vesper.util.date_range import DateRange


def tuple_to_date(t):
    return datetime.date(*t)


def date_to_tuple(d):
    return((d.year, d.month, d.day))


class DateRangeTests(TestCase):


    def test(self):
        
        cases = [
            
            # empty ranges
            ((2020, 1, 1), (2019, 12, 31), ()),
            ((2020, 1, 1), (2020, 1, 1), ()),
            
            # non-empty ranges
            ((2020, 1, 1), (2020, 1, 2), ((2020, 1, 1),)),
            ((2020, 1, 1), (2020, 1, 3), ((2020, 1, 1), (2020, 1, 2))),
            ((2019, 12, 31), (2020, 1, 2), ((2019, 12, 31), (2020, 1, 1))),
            ((2020, 2, 28), (2020, 3, 1), ((2020, 2, 28), (2020, 2, 29))),
            ((2019, 2, 28), (2019, 3, 1), ((2019, 2, 28),)),
            
        ]
        
        for start, stop, expected in cases:
            
            start = tuple_to_date(start)
            stop = tuple_to_date(stop)
            
            actual = tuple(date_to_tuple(d) for d in DateRange(start, stop))
            
            self.assertEqual(actual, expected)
