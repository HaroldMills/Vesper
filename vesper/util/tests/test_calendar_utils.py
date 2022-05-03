import calendar
import datetime

from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
from vesper.util.calendar_month import CalendarMonth
import vesper.util.calendar_utils as calendar_utils


class CalendarUtilsTests(TestCase):
    
    
    def test_get_calendar_periods(self):
        
        # In the cases for this method, we specify month names in the
        # forms `m1` through `m12` for January through December,
        # respectively, and translate them to month names in the current
        # locale using the `calendar.month_name` function.
        
        cases = [
                 
            ([], []),
            
            (['2016-05-01'], [('May 2016', '2016-05', '2016-05')]),
            
            (['2016-05-01', '2016-05-31'],
             [('m5 2016', '2016-05', '2016-05')]),
                 
            (['2016-05-01', '2016-06-01'],
             [('m5 - m6 2016', '2016-05', '2016-06')]),
                 
            (['2016-05-01', '2016-06-01', '2016-08-01'],
             [('m5 - m8 2016', '2016-05', '2016-08')]),
                   
            (['2016-05-01', '2016-06-01', '2016-09-01'],
             [('m5 - m6 2016', '2016-05', '2016-06'),
              ('m9 2016', '2016-09', '2016-09')]),
                   
            (['2016-05-01', '2016-06-01', '2016-09-01', '2017-01-01'],
             [('m5 - m6 2016', '2016-05', '2016-06'),
              ('m9 2016', '2016-09', '2016-09'),
              ('m1 2017', '2017-01', '2017-01')]),
                 
            (['2016-12-01', '2017-01-01'],
             [('m12 2016 - m1 2017', '2016-12', '2017-01')]),

        ]
        
        for dates, expected in cases:
            dates = _parse_dates(dates)
            expected = _parse_periods(expected)
            periods = calendar_utils.get_calendar_periods(dates)
            self.assertEqual(periods, expected) 


def _parse_dates(dates):
    return [_parse_date(d) for d in dates]


def _parse_date(date):
    year, month, day = date.split('-')
    return datetime.date(int(year), int(month), int(day))
        
        
def _parse_periods(periods):
    return [_parse_period(*p) for p in periods]


def _parse_period(name, start, end):
    name = _parse_name(name)
    start = _parse_month(start)
    end = _parse_month(end)
    return Bunch(name=name, start=start, end=end)
    
    
def _parse_name(name):
    parts = name.split('-')
    return '-'.join(_parse_name_part(p) for p in parts)


def _parse_name_part(part):
    parts = part.split(' ')
    return ' '.join(_parse_name_part_aux(p) for p in parts)


def _parse_name_part_aux(part):
    if part.startswith('m'):
        month_num = int(part[1:])
        return calendar.month_name[month_num]
    else:
        return part
    
        
def _parse_month(month):
    year, month = month.split('-')
    return CalendarMonth(int(year), int(month))
