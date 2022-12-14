"""
Script that evaluates the `SunMoon` class.

For one location, this script computes solar event times for all of
the nights of one year by three methods:

    1. with one call to get_solar_events_in_interval
    2. with one call per day to get_solar_events
    3. with one call per event to get_solar_event_time

For each method, the script reports how long it takes to get the
event times. It also checks that the three methods yield the same
events.
"""


from collections import namedtuple
import cProfile
import datetime
import itertools
import time

from vesper.ephem.sun_moon import SunMoonCache, Event
from vesper.util.date_range import DateRange


PROFILING_ENABLED = False

Location = namedtuple(
    'Location', ('latitude', 'longitude', 'time_zone', 'name'))

ITHACA = Location(42.4440, -76.5019, 'US/Eastern', 'Ithaca')
MISSOULA = Location(46.8721, -113.9940, 'US/Mountain', 'Missoula')

YEAR = 2020

SOLAR_EVENT_NAMES = (
    'Solar Midnight',
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise',
    'Solar Noon',
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk',
)

TIME_EQUALITY_THRESHOLD = .001


def main():
    
    cache = SunMoonCache()
    
    print('Getting events for two locations...')
    print()
    get_events_for_two_locations(cache)
    
    # We include this to test event caching. Getting solar events
    # should be fast here, since we computed all of them above.
    print('Getting events for two locations again...')
    print()
    get_events_for_two_locations(cache)


def get_events_for_two_locations(cache):
    for location in (ITHACA, MISSOULA):
        sun_moon = cache.get_sun_moon(
            location.latitude, location.longitude, location.time_zone)
        get_events_for_location(location.name, sun_moon)


def get_events_for_location(location_name, sun_moon):
    
    for day in (True, False):
        
        get_events_for_location_aux(location_name, sun_moon, day, False)
        
        # We include this to test event caching. Getting solar events
        # should be fast here, since we computed all of them above.
        get_events_for_location_aux(location_name, sun_moon, day, True)


def get_events_for_location_aux(location_name, sun_moon, day, again):
        
        day_or_night = 'day' if day else 'night'
        again = ' again' if again else ''
        
        print(f'Getting {day_or_night} events for {location_name}{again}...')
        
        by_year_events, by_year_time = \
            get_events(get_events_by_year, sun_moon, day, 'year')
        
        by_date_events, by_date_time = \
            get_events(get_events_by_date, sun_moon, day, day_or_night)
        
        by_name_events, by_name_time = \
            get_events(get_events_by_name, sun_moon, day, 'name')
        
        show_elapsed_time('year', by_year_time)
        show_elapsed_time(day_or_night, by_date_time)
        show_elapsed_time('name', by_name_time)
        
        compare_events(day_or_night, by_date_events, 'year', by_year_events)
        compare_events('name', by_name_events, 'year', by_year_events)
        
        print()


def get_events(function, sun_moon, day, method):
    
    print(f'Getting events by {method}...')
    
    start_time = time.time()
    
    if PROFILING_ENABLED:
        runner = Runner(function, sun_moon, day)
        cProfile.runctx('runner.run()', globals(), locals())
        events = runner.result
    
    else:
        events = function(sun_moon, day)
    
    elapsed_time = time.time() - start_time
    
    return events, elapsed_time


def get_events_by_year(sun_moon, day):
    time_zone = sun_moon.time_zone
    hour = 0 if day else 12
    start_dt = datetime.datetime(YEAR, 1, 1, hour, tzinfo=time_zone)
    end_dt = datetime.datetime(YEAR + 1, 1, 1, hour, tzinfo=time_zone)
    return sun_moon.get_solar_events_in_interval(start_dt, end_dt)


def get_events_by_date(sun_moon, day):
    start_date = datetime.date(YEAR, 1, 1)
    end_date = datetime.date(YEAR + 1, 1, 1)
    event_lists = [
        sun_moon.get_solar_events(date, day=day)
        for date in DateRange(start_date, end_date)]
    return list(itertools.chain.from_iterable(event_lists))


def get_events_by_name(sun_moon, day):
    start_date = datetime.date(YEAR, 1, 1)
    end_date = datetime.date(YEAR + 1, 1, 1)
    event_lists = [
        get_solar_events_by_name(sun_moon, date, day)
        for date in DateRange(start_date, end_date)]
    return list(itertools.chain.from_iterable(event_lists))


def get_solar_events_by_name(sun_moon, date, day):
    events = [
        get_solar_event(sun_moon, date, name, day)
        for name in SOLAR_EVENT_NAMES]
    return sorted(e for e in events if e is not None)


def get_solar_event(sun_moon, date, event_name, day):
    time = sun_moon.get_solar_event_time(date, event_name, day=day)
    if time is None:
        return None
    else:
        return Event(time, event_name)


def show_elapsed_time(method, elapsed_time):
    print(f'Getting events by {method} took {elapsed_time:.1f} seconds.')


def compare_events(method_a, events_a, method_b, events_b):
    
    if len(events_a) != len(events_b):
        
        print(
            f'Got {len(events_a)} events by {method_a} but '
            f'{len(events_b)} by {method_b}.')
        return
    
    else:
        
        for i in range(len(events_a)):
            
            a = events_a[i]
            b = events_b[i]
            
            # print(f'{a.name}: {a.time}, {b.name}: {b.time}')
            
            if a.name != b.name or times_differ(a.time, b.time):
                print(
                    f'Events by {method_a} differ from events by {method_b}.')
                return
        
        # If we get here, the two sets of events were the same.
        print(f'Got same events by {method_a} and {method_b}.')


def times_differ(a, b):
    return abs((a - b).total_seconds()) > TIME_EQUALITY_THRESHOLD


class Runner:
    
    
    def __init__(self, function, *args):
        self.function = function
        self.args = args
    
    
    def run(self):
        self.result = self.function(*self.args)


if __name__ == '__main__':
    main()
