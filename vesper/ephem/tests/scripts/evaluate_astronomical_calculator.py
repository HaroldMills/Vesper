"""
Script that evaluates the `AstronomicalCalculator` class.

For one location, this script computes twilight event times for all of
the nights of one year by three methods:

    1. with one call to get_twilight_events
    2. with one call per day to get_night_twilight_events
    3. with one call per event to get_night_twilight_event_time

For each method, the script reports how long it takes to get the
event times. It also checks that the three methods yield the same
events.
"""


from collections import namedtuple
import cProfile
import datetime
import itertools
import time

from vesper.ephem.astronomical_calculator import (
    AstronomicalCalculatorCache, Event)
from vesper.util.date_range import DateRange


PROFILING_ENABLED = False

Location = namedtuple(
    'Location', ('latitude', 'longitude', 'time_zone', 'name'))

ITHACA = Location(42.4440, -76.5019, 'US/Eastern', 'Ithaca')
MISSOULA = Location(46.8721, -113.9940, 'US/Mountain', 'Missoula')

YEAR = 2020

TWILIGHT_EVENT_NAMES = (
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise',
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk',
)

TIME_EQUALITY_THRESHOLD = .001


def main():
    
    cache = AstronomicalCalculatorCache()
    
    print('Getting events for two locations...')
    print()
    get_events_for_two_locations(cache)
    
    print('Getting events for two locations again...')
    print()
    get_events_for_two_locations(cache)


def get_events_for_two_locations(cache):
    for location in (ITHACA, MISSOULA):
        calculator = cache.get_calculator(
            location.latitude, location.longitude, location.time_zone)
        get_events_for_location(location.name, calculator)


def get_events_for_location(location_name, calculator):
    
    for day in (True, False):
        
        get_events_for_location_aux(location_name, calculator, day, False)
        
        # We include this to test event caching. Getting twilight events
        # for one day or night should be much faster the second time
        # around.
        get_events_for_location_aux(location_name, calculator, day, True)


def get_events_for_location_aux(location_name, calculator, day, again):
        
        day_or_night = 'day' if day else 'night'
        again = ' again' if again else ''
        
        print(f'Getting {day_or_night} events for {location_name}{again}...')
        
        by_year_events, by_year_time = \
            get_events(get_events_by_year, calculator, day, 'year')
        
        by_date_events, by_date_time = \
            get_events(get_events_by_date, calculator, day, day_or_night)
        
        by_name_events, by_name_time = \
            get_events(get_events_by_name, calculator, day, 'name')
        
        show_elapsed_time('year', by_year_time)
        show_elapsed_time(day_or_night, by_date_time)
        show_elapsed_time('name', by_name_time)
        
        compare_events(day_or_night, by_date_events, 'year', by_year_events)
        compare_events('name', by_name_events, 'year', by_year_events)
        
        print()


def get_events(function, calculator, day, method):
    
    print(f'Getting events by {method}...')
    
    start_time = time.time()
    
    if PROFILING_ENABLED:
        runner = Runner(function, calculator, day)
        cProfile.runctx('runner.run()', globals(), locals())
        events = runner.result
    
    else:
        events = function(calculator, day)
    
    elapsed_time = time.time() - start_time
    
    return events, elapsed_time


def get_events_by_year(calculator, day):
    time_zone = calculator.time_zone
    hour = 0 if day else 12
    start_dt = time_zone.localize(datetime.datetime(YEAR, 1, 1, hour))
    end_dt = time_zone.localize(datetime.datetime(YEAR + 1, 1, 1, hour))
    return calculator.get_twilight_events(start_dt, end_dt)


def get_events_by_date(calculator, day):
    start_date = datetime.date(YEAR, 1, 1)
    end_date = datetime.date(YEAR + 1, 1, 1)
    event_lists = [
        get_date_twilight_events(calculator, date, day)
        for date in DateRange(start_date, end_date)]
    return list(itertools.chain.from_iterable(event_lists))


def get_date_twilight_events(calculator, date, day):
    if day:
        return calculator.get_day_twilight_events(date)
    else:
        return calculator.get_night_twilight_events(date)


def get_events_by_name(calculator, day):
    start_date = datetime.date(YEAR, 1, 1)
    end_date = datetime.date(YEAR + 1, 1, 1)
    event_lists = [
        get_date_twilight_events_by_name(calculator, date, day)
        for date in DateRange(start_date, end_date)]
    return list(itertools.chain.from_iterable(event_lists))


def get_date_twilight_events_by_name(calculator, date, day):
    events = [
        get_date_twilight_event(calculator, date, name, day)
        for name in TWILIGHT_EVENT_NAMES]
    return sorted(e for e in events if e is not None)


def get_date_twilight_event(calculator, date, event_name, day):
    
    if day:
        time = calculator.get_day_twilight_event_time(date, event_name)
    else:
        time = calculator.get_night_twilight_event_time(date, event_name)
    
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
