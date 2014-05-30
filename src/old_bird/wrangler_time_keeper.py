"""Module containing class `WranglerTimeKeeper`."""


import datetime
import re

import nfc.util.time_utils as time_utils


_ONE_HOUR = datetime.timedelta(hours=1)
_ONE_DAY = datetime.timedelta(days=1)


class WranglerTimeKeeper(object):
    
    """
    Auxiliary time-keeping class for the NFC wrangler.
    
    An instance of this class can be queried for DST start and end times
    and monitoring start times for the stations of a monitoring network.
    """
    
    
    def __init__(
        self, default_dst_intervals, dst_intervals, monitoring_start_times):
        
        self._dst_years = frozenset(default_dst_intervals.keys())
        
        self._default_dst_intervals = \
            _parse_default_dst_intervals(default_dst_intervals)
            
        self._dst_intervals = _parse_dst_intervals(dst_intervals)
        
        self._monitoring_start_times = \
            _parse_monitoring_start_times(monitoring_start_times)
        
        
    def is_time_ambiguous(self, time, station_name):
        
        """
        Tests if the specified local time is ambiguous because of its
        proximity to the end of DST.
        
        A local time in the interval [1:00:00, 2:00:00) on the night that
        DST ends is ambiguous since both the hour before DST ends and the
        hour after DST ends map to that interval.
        """
        
        self._check_year(time.year)
        
        interval = self._get_dst_interval(time.year, station_name)
        
        if interval is None:
            return False
        
        else:
            _, dst_end_time = interval
            return time >= dst_end_time - _ONE_HOUR and time < dst_end_time
                  
                   
    def _check_year(self, year):
        if year not in self._dst_years:
            f = 'DST start and end times not available for year {:d}.'
            raise ValueError(f.format(year))
        
        
    def _get_dst_interval(self, year, station_name):
        
        intervals = self._dst_intervals.get(year)
        if intervals is None:
            return self._default_dst_intervals.get(year)
        
        try:
            return intervals[station_name]
        except KeyError:
            return self._default_dst_intervals.get(year)
        
        
    def get_monitoring_start_time(self, station_name, night):
        
        """
        Gets the time monitoring started for the specified station and night.
        """
        
        try:
            times = self._monitoring_start_times
            return times[night.year][station_name][night]
        except KeyError:
            return None
        
            
    def resolve_elapsed_time(self, station_name, night, time_delta):
        
        """Resolves an elapsed time for the specified station and night."""
        
        start_time = self.get_monitoring_start_time(station_name, night)
        if start_time is None:
            return None
        else:
            return start_time + time_delta
        
        
def _parse_default_dst_intervals(intervals):
    return dict(_parse_default_dst_item(i) for i in intervals.iteritems())
        

def _parse_default_dst_item(item):
    year, (start, end) = item
    start = _parse_date_time(start, year)
    end = _parse_date_time(end, year)
    return (year, (start, end))
    

def _parse_date_time(s, year):
    
    parts = s.split()
    if len(parts) != 2:
        raise ValueError('Bad date and time "{:s}".'.format(s))
    
    d, t = parts
    d = _parse_date(d, year)
    t = _parse_time(t)
    
    return datetime.datetime(
               d.year, d.month, d.day, t.hour, t.minute, t.second)
    
    
_DATE_RE = re.compile(r'(\d\d?)-(\d\d?)')


def _parse_date(s, year):
    
    m = _DATE_RE.match(s)
    
    if m is None:
        _handle_bad_date(s)
    
    else:
        
        month, day = m.groups()
        
        month = int(month)
        day = int(day)
        
        try:
            time_utils.check_month(month)
            time_utils.check_day(day, year, month)
            
        except ValueError:
            _handle_bad_date(s)
            
        return datetime.date(year, month, day)
    

def _handle_bad_date(s):
    raise ValueError('Bad date "{:s}".'.format(s))

    
_TIME_RE = re.compile(r'(\d\d?):(\d\d):(\d\d)')


def _parse_time(s):
    
    m = _TIME_RE.match(s)
    
    if m is None:
        _handle_bad_time(s)
    
    else:
        
        hour, minute, second = m.groups()
        
        hour = int(hour)
        minute = int(minute)
        second = int(second)
        
        try:
            time_utils.check_hour(hour)
            time_utils.check_minute(minute)
            time_utils.check_second(second)
            
        except ValueError:
            _handle_bad_time(s)
            
        return datetime.time(hour, minute, second)


def _handle_bad_time(s):
    raise ValueError('Bad time "{:s}"'.format(s))


def _parse_dst_intervals(intervals):
    return dict(_parse_dst_item(*i) for i in intervals.iteritems())
        

def _parse_dst_item(year, intervals):
    return (year, dict(_parse_dst_item_aux(year, *i)
                       for i in intervals.iteritems()))


def _parse_dst_item_aux(year, station_name, times):
    
    if times is not None:
        start, end = times
        start = _parse_date_time(start, year)
        end = _parse_date_time(end, year)
        times = (start, end)
        
    return (station_name, times)


def _parse_monitoring_start_times(times):
    return dict(_parse_monitoring_item(*i) for i in times.iteritems())


def _parse_monitoring_item(year, times):
    return (year, dict(_parse_monitoring_item_aux(year, *i)
                       for i in times.iteritems()))
    
    
def _parse_monitoring_item_aux(year, station_name, (time, dates)):
    
    time = _parse_time(time)
    _combine = datetime.datetime.combine
    
    if len(dates) == 0:
        
        # Assign time to each day of year.
        times = dict((date, _combine(date, time))
                     for date in _get_all_dates(year))
        
    else:
        
        times = {}
        
        for item in dates:
            
            if isinstance(item, tuple):
                
                start, end = item
                start = _parse_date(start, year)
                end = _parse_date(end, year)
                
                if start > end:
                    raise ValueError(
                        ('Start date {:s} follows end date {:s} for '
                         'monitoring start times specified for station '
                         '"{:s}" for {:d}.').format(
                             start, end, station_name, year))
                    
                end += _ONE_DAY
                
                date = start
                while date != end:
                    times[date] = _combine(date, time)
                    date += _ONE_DAY
                    
            else:
                # item is not a `tuple`, so it should be a date string
                
                date = _parse_date(item, year)
                times[date] = _combine(date, time)
            
    return station_name, times


def _get_all_dates(year):
    start = datetime.date(year, 1, 1).toordinal()
    end = datetime.date(year + 1, 1, 1).toordinal()
    return [datetime.date.fromordinal(i) for i in xrange(start, end)]
