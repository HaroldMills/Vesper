"""Module containing class `ArchiverTimeKeeper`."""


import datetime
import re

import pytz

import vesper.util.time_utils as time_utils


_ONE_HOUR = datetime.timedelta(hours=1)
_ONE_DAY = datetime.timedelta(days=1)
_ZERO = datetime.timedelta()


class NonexistentTimeError(Exception):
    pass


class AmbiguousTimeError(Exception):
    pass


class ArchiverTimeKeeper(object):
    
    """
    Auxiliary time-keeping class for the Vesper archiver.
    
    An instance of this class can convert both naive and elapsed
    monitoring times to UTC.
    """
    
    
    def __init__(self, stations, time_zone_names, start_times):
        
        """
        Mapping from station names to monitoring time zone names.
        
        :Parameters:
        
            stations: mapping
                Mapping from station names to station objects.
                
                Each station object must have `name` and `time_zone_name`
                attributes. The `time_zone_name` must be a name known to
                the Olson time zone database, suitable as an argument to
                the `pytz.timezone` function.
                
            time_zone_names : mapping
                Mapping from station names to monitoring time zone names.
        
                The time zone name must be known to the Olson time zone
                database, suitable as an argument to the `pytz.timezone`
                function.
                
                The monitoring time zone for a station may be different
                from the station time zone, and in fact it *should* be if
                the station time zone observes DST, since otherwise the
                times of some clip files may be ambiguous.
                
            start_times : mapping
                Mapping from years to station names to monitoring start times.
                
                The monitoring start times for a particular year and station
                are expressed as a `(time, dates)` pair. The time of each
                pair is a string of the form *HH:MM:SS*. The hour field can
                contain either one or two digits and should be in the range
                [0, 23]. The minute and second fields must each contain
                two digits. The dates are a list of items, with each item
                either a date string of the form *MM-DD*, representing a
                single date, or a pair of start and end dates, representing
                a range of dates. The month and day fields of a date string
                can contain either one or two digits. A monitoring start
                time should be for the monitoring time zone of the
                appropriate station, *not* the station time zone (unless
                the two are the same, which they often should not be to
                avoid DST ambiguities).
        """

        stations = stations.values()
        self._time_zones = _get_time_zones(stations, time_zone_names)
        self._start_times = self._parse_start_times(start_times)
        
        
    def convert_naive_time_to_utc(self, time, station_name):
        
        time_zone = self._time_zones[station_name]
        
        # We must specify `is_dst=None` here for the `localize` method
        # to raise an exception if the naive time is either nonexistent
        # or ambiguous. If we omit the `is_dst` argument the method will
        # *not* raise an exception if the naive time is nonexistent or
        # ambiguous, but rather yield the specified time with the
        # standard time (as opposed to daylight time) offset.
        try:
            time = time_zone.localize(time, is_dst=None)
        except pytz.NonExistentTimeError as e:
            raise NonexistentTimeError(str(e))
        except pytz.AmbiguousTimeError as e:
            raise AmbiguousTimeError(str(e))
        
        return time.astimezone(pytz.utc)
    
    
    def convert_elapsed_time_to_utc(self, time_delta, station_name, night):
        try:
            start_time = self._start_times[night.year][station_name][night]
        except KeyError:
            return None
        else:
            return start_time + time_delta
        
            
    def _parse_start_times(self, times):
        return dict(self._parse_start_times_item(*i)
                    for i in times.iteritems())
    
    
    def _parse_start_times_item(self, year, times):
        return (year, dict(self._parse_start_times_item_aux(year, *i)
                           for i in times.iteritems()))
        
        
    def _parse_start_times_item_aux(self, year, station_name, (time, dates)):
        
        self._station_name = station_name
        time = _parse_time(time)
        to_utc = self._to_utc
        
        if len(dates) == 0:
            
            # Assign time to each day of year.
            times = dict((date, to_utc(date, time))
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
                        times[date] = to_utc(date, time)
                        date += _ONE_DAY
                        
                else:
                    # item is not a `tuple`, so it should be a date string
                    
                    date = _parse_date(item, year)
                    times[date] = to_utc(date, time)
                
        return station_name, times


    def _to_utc(self, date, time):
        dt = datetime.datetime.combine(date, time)
        return self.convert_naive_time_to_utc(dt, self._station_name)
    

def _get_time_zones(stations, time_zone_names):
    return dict(_get_time_zone_data(s, time_zone_names) for s in stations)


def _get_time_zone_data(station, time_zone_names):
    time_zone_name = time_zone_names.get(station.name, station.time_zone.zone)
    time_zone = pytz.timezone(time_zone_name)
    return (station.name, time_zone)


_TIME_RE = re.compile(r'^(\d\d?):(\d\d):(\d\d)$')


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


def _get_all_dates(year):
    start = datetime.date(year, 1, 1).toordinal()
    end = datetime.date(year + 1, 1, 1).toordinal()
    return [datetime.date.fromordinal(i) for i in xrange(start, end)]


_DATE_RE = re.compile(r'^(\d\d?)-(\d\d?)$')
 
 
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
