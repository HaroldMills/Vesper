"""Utility functions pertaining to calendars."""


import calendar
import datetime
import json

from vesper.util.bunch import Bunch
from vesper.util.calendar_month import CalendarMonth


_CALENDAR_GAP_THRESHOLD = 2
_MONTH_NAMES = calendar.month_name


def get_calendar_periods_json(periods, clip_counts):
    period_dicts = [_create_period_dict(p, clip_counts) for p in periods]
    return json.dumps(period_dicts)


def _create_period_dict(period, clip_counts):
    num_months = period.end - period.start + 1
    months = list(period.start + i for i in range(num_months))
    month_dicts = [_create_month_dict(m, clip_counts) for m in months]
    return {
        'name': period.name,
        'months': month_dicts
    }


def _create_month_dict(month, clip_counts):
    day_counts = _create_day_counts_list(month, clip_counts)
    return {
        'year': month.year,
        'month': month.month,
        'dayCounts': day_counts
    }


def _create_day_counts_list(month, clip_counts):
    _, num_days = calendar.monthrange(month.year, month.month)
    day_counts = {}
    for day in range(1, num_days + 1):
        date = datetime.date(month.year, month.month, day)
        count = clip_counts.get(date)
        if count is not None:
            day_counts[day] = count
    return sorted(day_counts.items())
    
    
def get_calendar_periods(dates):
    months = _get_unique_months(dates)
    return _get_calendar_periods(months)


def _get_unique_months(dates):
    months = frozenset(CalendarMonth(d.year, d.month) for d in dates)
    return sorted(list(months))
    
    
def _get_calendar_periods(months):
    
    if len(months) == 0:
        return []
    
    else:
        # have at least one month
        
        spans = []
        
        # Start a span at the first month.
        start = months[0]
        prev = months[0]
        
        for month in months[1:]:
            
            num_empty_months = month - prev - 1
            
            if num_empty_months >= _CALENDAR_GAP_THRESHOLD:
                # enough empty months to warrant a calendar gap
                
                # End current span and start another.
                spans.append((start, prev))
                start = month
                
            prev = month
            
        # End current span.
        spans.append((start, prev))
        
        return [_create_period(*s) for s in spans]


def _create_period(start, end):
    name = _create_period_name(start, end)
    return Bunch(name=name, start=start, end=end)


def _create_period_name(start, end):
    
    if start == end:
        month_name = _MONTH_NAMES[start.month]
        return '{} {}'.format(month_name, start.year)
        
    else:
        
        start_name = _MONTH_NAMES[start.month]
        end_name = _MONTH_NAMES[end.month]
        
        if start.year == end.year:
            return '{} - {} {}'.format(start_name, end_name, start.year)
        
        else:
            return '{} {} - {} {}'.format(
                start_name, start.year, end_name, end.year)


# TODO: Delete this if it is no longer needed after Qt GUI is gone.
def get_year_month_string(year, month):
    date = datetime.date(year, month, 1)
    return datetime.datetime.strftime(date, '%B %Y')
