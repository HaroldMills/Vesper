"""Module containing class `AstronomicalCalculator`."""


from collections import namedtuple
from functools import lru_cache
from pathlib import Path
import datetime
import pytz

from skyfield import almanac
from skyfield.api import Topos, load, load_file

from vesper.util.lru_cache import LruCache


# TODO: Eliminate `Location` class, or require it for `get_calculator`?
# TODO: Make time zone optional and drop support for local time results?
# TODO: Reconsider "time" versus "datetime".


_EPHEMERIS_FILE_PATH = Path(__file__).parent / 'data' / 'de421.bsp'
"""
Jet Propulsion Laboratory Development Ephemeris (JPL DE) Spice Planet
Kernel (SPK) file path. See
en.wikipedia.org/wiki/Jet_Propulsion_Laboratory_Development_Ephemeris
for a discussion of the JPL DE.

See https://pypi.org/project/jplephem/ for instructions on excerpting
SPK files. This might be a good idea to reduce the SPK file size.
"""

_SOLAR_EVENT_NAMES = {
    (0, 1): 'Astronomical Dawn',
    (1, 2): 'Nautical Dawn',
    (2, 3): 'Civil Dawn',
    (3, 4): 'Sunrise',
    (4, 3): 'Sunset',
    (3, 2): 'Civil Dusk',
    (2, 1): 'Nautical Dusk',
    (1, 0): 'Astronomical Dusk'
}

_RISING_EVENT_NAMES = frozenset((
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise'
))

_SETTING_EVENT_NAMES = frozenset((
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk'
))

_SOLAR_PERIOD_NAMES = {
    0: 'Night',
    1: 'Astronomical Twilight',
    2: 'Nautical Twilight',
    3: 'Civil Twilight',
    4: 'Day'
}

_ONE_DAY = datetime.timedelta(days=1)
_THIRTEEN_HOURS = datetime.timedelta(hours=13)


'''
AstronomicalCalculator methods:

def __init__(self, location, result_times_local=False)

@property
def location(self)

@property
def result_times_local(self)

def get_solar_position(self, time)

def get_solar_noon(self, date)

def get_solar_midnight(self, date)

def get_solar_events(self, start_time, end_time, event_names=None)

def get_day_solar_events(self, date, event_names=None)

def get_day_solar_event_time(self, date, event_name)

def get_night_solar_events(self, date, event_names=None)

def get_night_solar_event_time(self, date, event_name)

def get_solar_period_name(self, time)
    
def get_lunar_position(self, time)
    
def get_lunar_fraction_illuminated(self, time)


Omit the following methods initially. Skyfield does not yet offer
moonrise and moonset calculations. It is more difficult to calculate
rise and set events for the moon than the sun because of the nearness
of the moon to the earth and the eccentricity of the moon's orbit.
These make the angle subtended by the moon more variable than the
angle subtended by the sun.

def get_lunar_events(self, start_time, end_time, name_filter=None)

def is_moon_up(self, time)
'''


'''
Solar period definitions, with numbers in degrees:

Night: altitude < -18
Astronomical Twilight: -18 <= altitude < -12
Nautical Twilight: -12 <= altitude < -6
Civil Twilight: -6 <= altitude < -.833333
Day: altitude >= -8.33333
'''


Position = namedtuple('Position', ('altitude', 'azimuth', 'distance'))
"""
Position of the sun or moon in the sky.

A `Position` is a `namedtuple` with three attributes: `altitude`,
`azimuth`, and `distance`. The altitude and azimuth are in degrees,
and the distance is in kilometers.
"""


Event = namedtuple('Event', ('time', 'name'))
"""
Astronomical event, for example sunrise or sunset.

An `Event` is a `namedtuple` with two attributes: `time` and `name`.
The time is a Python `datetime` and the name is a string.
"""


class Location:
    
    """
    A location on the earth.
    
    A `Location` has a latitude, longitude, time zone, and optional
    name. `Location` objects are hashable, and two `Location` objects
    are considered equal if they have the same latitude, longitude,
    and time zone.
    """
    
    
    def __init__(self, latitude, longitude, time_zone, name=None):
        
        self._latitude = latitude
        self._longitude = longitude
        
        if isinstance(time_zone, str):
            self._time_zone = pytz.timezone(time_zone)
        else:
            self._time_zone = time_zone
        
        self._name = name
    
    
    @property
    def latitude(self):
        return self._latitude
    
    
    @property
    def longitude(self):
        return self._longitude
    
    
    @property
    def time_zone(self):
        return self._time_zone
    
    
    @property
    def name(self):
        return self._name
    
    
    def __eq__(self, other):
        if not isinstance(other, Location):
            return False
        else:
            return (
                self._latitude == other.latitude and
                self._longitude == other.longitude and
                self._time_zone == other.time_zone)
    
    
    def __hash__(self):
        return hash((self._latitude, self._longitude, self._time_zone))


class AstronomicalCalculator:
    
    
    """
    Solar and lunar astronomical calculator for a single location.
    
    An `AstronomicalCalculator` calculates various quantities
    related to the observation of the sun and the moon from a
    particular location on the earth. The quantities include the
    positions of the sun and moon in the sky, the times of events
    (like sunrise and sunset) defined in terms of the altitude of
    the sun, and the illuminated fraction of the moon.
    
    An `AstronomicalCalculator` performs all computations for an
    observer at sea level, since quantities computed at other
    (realistic, terrestrial) elevations seem to differ only very
    slightly from those. For example, sunrise times for observers
    at sea level and an elevation of 10,000 meters (i.e. higher
    than the top of Mount Everest) differ by only about a
    millisecond at the latitude and longitude of Ithaca, New York.
    
    The `location` initializer argument must have the three
    attributes `latitude`, `longitude`, and `time_zone`. The `latitude`
    and `longitude` attributes must be numbers with units of degrees.
    The `time_zone` attribute can be either a string IANA time zone
    name (e.g. "US/Eastern") or a `datetime.tzinfo` subclass, including
    a `pytz` time zone.
    
    Note that it is essential for the correct functioning of the
    various methods of this class that yield event times for a
    particular date (including the `get_solar_noon`,
    `get_solar_midnight`, `get_day_solar_events`,
    `get_night_solar_events`, `get_day_solar_event_time`, and
    `get_night_solar_event_time` methods) that an
    `AstronomicalCalculator` know the time zone of its location.
    It is only with such a time zone that the methods can relate
    a time on a specific date to the correct UTC time for any
    location on earth, including all locations near the
    international date line.
    
    The `result_times_local` initializer argument determines whether
    times returned by the methods of a calculator are in the local
    time zone or UTC.
    
    Methods that have `datetime` arguments require that those arguments
    be time-zone-aware.
    
    Several of the methods of this class cache results to improve the
    efficiency of repeated invocations with the same arguments. These
    methods are:
    
        * get_solar_position
        * get_solar_noon
        * get_solar_midnight
        * get_day_solar_events
        * get_night_solar_events
        * get_day_solar_event_time
        * get_night_solar_event_time
        * get_lunar_position
    
    """
    
    
    # The cache size is fixed instead of an initializer argument since
    # we use the `functools.lru_cache` decorator to implement caching.
    _MAX_CACHE_SIZE = 1000
    
    _ephemeris = None
    _sun = None
    _earth = None
    _moon = None
    _timescale = None
    
    
    @classmethod
    def _init_if_needed(cls):
        if cls._ephemeris is None:
            cls._ephemeris = load_file(_EPHEMERIS_FILE_PATH)
            cls._sun = cls._ephemeris['sun']
            cls._earth = cls._ephemeris['earth']
            cls._moon = cls._ephemeris['moon']
            cls._timescale = load.timescale()
    
    
    def __init__(self, location, result_times_local=False):
        
        AstronomicalCalculator._init_if_needed()
        
        self._location = _get_location(location)
        self._result_times_local = result_times_local
        
        # See comment in class docstring about why we perform all
        # computations for an observer at zero elevation, i.e. at sea level.
        self._topos = Topos(
            latitude_degrees=location.latitude,
            longitude_degrees=location.longitude,
            elevation_m=0)
        
        self._loc = self._earth + self._topos
        
        self._solar_noon_midnight_function = \
            almanac.meridian_transits(self._ephemeris, self._sun, self._topos)
        
        self._solar_period_function = \
            almanac.dark_twilight_day(self._ephemeris, self._topos)
    
    
    @property
    def location(self):
        return self._location
    
    
    @property
    def result_times_local(self):
        return self._result_times_local
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_solar_position(self, time):
        return self._get_position(self._sun, time)
    
    
    def _get_position(self, body, time):
        
        # Get Skyfield position.
        time = self._get_skyfield_time(time)
        position = self._loc.at(time).observe(body).apparent().altaz()
        
        # Get position attributes with desired units.
        altitude = position[0].degrees
        azimuth = position[1].degrees
        distance = position[2].km
        
        return Position(altitude, azimuth, distance)
    
    
    def _get_skyfield_time(self, arg):
        
        if isinstance(arg, datetime.datetime):
            return self._get_scalar_skyfield_time(arg)
            
        else:
            # assume `arg` is iterable of `datetime` objects
            
            # We create a list from the iterable since the documentation
            # for the Skyfield `Timescale.from_datetimes` method specifies
            # that its argument should be a list of `datetime` objects.
            times = list(arg)
            
            for time in times:
                _check_time_zone_awareness(time)
                
            return self._timescale.from_datetimes(times)
        
        
    def _get_scalar_skyfield_time(self, time):
        _check_time_zone_awareness(time)
        return self._timescale.from_datetime(time)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_solar_noon(self, date):
        return self._get_solar_noon_or_midnight(date, True)
    
    
    def _get_solar_noon_or_midnight(self, date, noon):
        
        # Get start hour of day and duration in hours of period that
        # includes desired solar noon or midnight. We use a period
        # from four hours before noon or midnight in the local time
        # zone to account for the full range of possible differences
        # between local clock time and local solar time all over the
        # earth.
        start_hour = 8 if noon else 20
        duration = 8
        
        # Note that it is essential for the correct functioning of
        # this method that we use the local time zone of this
        # calculator's location to construct the start time of
        # the search interval for the desired solar noon or midnight.
        # It is only with such a time zone that the method can relate
        # a time on a specific date to the correct UTC time for any
        # location on earth, including all locations near the
        # international date line.
        #
        # Note that this is the only place in this class where we
        # use the local time zone, except for those where we convert
        # result times to it. The usage is essential, however, for
        # all methods that find events by date, including the
        # `get_solar_noon`, `get_solar_midnight`, `get_day_solar_events`,
        # `get_night_solar_events`, `get_day_solar_event_time`, and
        # `get_night_solar_event_time` methods.
        local_start_time = _create_aware_datetime(
            self.location.time_zone, date.year, date.month, date.day,
            start_hour)
        
        start_time = self._timescale.from_datetime(local_start_time)
        
        local_end_time = local_start_time + datetime.timedelta(hours=duration)
        end_time = self._timescale.from_datetime(local_end_time)
        
        ts, _ = almanac.find_discrete(
            start_time, end_time, self._solar_noon_midnight_function)
        
        time = ts[0].utc_datetime()
        
        if self.result_times_local:
            time = time.astimezone(self.location.time_zone)
            
        return time
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_solar_midnight(self, date):
        return self._get_solar_noon_or_midnight(date, False)
           
    
    def get_solar_events(self, start_time, end_time, name_filter=None):
        
        # Get start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_time)
        end_time = self._get_scalar_skyfield_time(end_time)
        
        # Get solar event times and codes.
        times, codes = almanac.find_discrete(
            start_time, end_time, self._solar_period_function)
        
        # Get event times as UTC `datetime` objects.
        times = [t.utc_datetime() for t in times]
        
        # Convert event times from UTC to local time zone if needed.
        if self.result_times_local:
            time_zone = self.location.time_zone
            times = [time.astimezone(time_zone) for time in times]

        # Get event names.
        names = self._get_solar_event_names(times, codes)
        
        # Create event named tuples.
        events = [Event(time, name) for time, name in zip(times, names)]
        
        # Filter events by name if needed.
        events = _filter_events(events, name_filter)
        
        return events
    
    
    def _get_solar_event_names(self, times, codes):
        
        event_count = len(codes)
        
        if event_count == 0:
            return []
        
        else:
            # have at least one event
            
            first_event_name = \
                self._get_first_solar_event_name(times[0], codes[0])
            
            other_event_names = [
                _get_solar_event_name(codes[i], codes[i + 1])
                for i in range(event_count - 1)]
            
            return [first_event_name] + other_event_names
            
            
    def _get_first_solar_event_name(self, time, code):
        
        if code == 0:
            # event is at start of night
            
            return 'Astronomical Dusk'
        
        elif code == 4:
            # event is at start of day
            
            return 'Sunrise'
        
        else:
            # code could indicate either of two events
            
            altitude = self.get_solar_position(time).altitude
            
            if code == 1:
                # event is at start of astronomical twilight
                
                if altitude < -15:
                    # sun ascended from night into astronomical twilight
                
                    return 'Astronomical Dawn'
                
                else:
                    # sun descended from nautical twilight into astronomical
                    # twilight
                    
                    return 'Nautical Dusk'
                
            elif code == 2:
                # event is at start of nautical twilight
                
                if altitude < -9:
                    # sun ascended from astronomical twilight into nautical
                    # twilight
                    
                    return 'Nautical Dawn'
                
                else:
                    # sun descended from civil twilight into nautical twilight
                    
                    return 'Civil Dusk'
                
            else:
                # even is at start of civil twilight
                
                if altitude < -3:
                    # sun ascended from nautical twilight into civil twilight
                    
                    return 'Civil Dawn'
                
                else:
                    # sun descended from day into civil twilight
                    
                    return 'Sunset'
            
            
    def get_day_solar_events(self, date, name_filter=None):
        events = self._get_day_solar_events(date)
        return _filter_events(events, name_filter)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_day_solar_events(self, date):
        return self._get_date_solar_events(date, True)
    
    
    def _get_date_solar_events(self, date, day):
        
        """
        Gets solar events for the specified day or night.
        
        The `_get_day_solar_events` and `_get_night_solar_events` methods
        both call this one, the `_get_day_solar_events` method to get
        solar rise/set events that occur between one solar midnight and
        the next, and the `_get_night_solar_events` method to get events
        that occur between one solar noon and the next. In both cases,
        there is at most one event of each event type during the relevant
        time interval. Some or all events do not occur at higher latitudes
        for some days, e.g. during the summer and winter.
        
        We rely on Skyfield to find solar event times. It can tell us
        the times and types of events that occur during any specified
        time interval. In order to avoid losing events due to edge
        effects, when searching for day solar events we do not simply
        search for the events from one solar midnight to the next,
        but rather for the events in an expanded time interval that
        extends from about an hour before the first solar midnight to
        about an hour after the second one. When searching for the
        night solar events, we expand the search interval analogously,
        to about one hour before one solar noon to about one hour after
        the next. While this guarantees that we will not lose any of
        the desired events to edge effects, it sometimes yields extra
        events, so that we wind up with two events of the same type
        for the expanded search interval rather than just the one we
        want. For example, when searching for day events it can yield
        two astronomical dawns or dusks, one near the beginning of the
        search interval and the other near the end. We can easily
        detect and discard such extra events, however. For day events,
        they are either setting events (i.e. sunset and the various
        dusk events) prior to solar noon or rising events (i.e. the
        various dawn events and sunrise) following solar noon. For
        night events, they are either rising events prior to solar
        midnight or setting events prior to solar noon.
        """
        
        
        # Get time interval to search for events.
        transit_time = self._get_solar_noon_or_midnight(date, day)
        start_time = transit_time - _THIRTEEN_HOURS
        end_time = transit_time + _THIRTEEN_HOURS
        
        # Get events in time interval.
        events = self.get_solar_events(start_time, end_time)
        
        # Discard extra events (see docstring for this method for more).
        events = _discard_extra_events(events, day, transit_time)
        
        return events
    
    
    def get_night_solar_events(self, date, name_filter=None):
        events = self._get_night_solar_events(date)
        return _filter_events(events, name_filter)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_night_solar_events(self, date):
        return self._get_date_solar_events(date, False)
    
    
    def get_day_solar_event_time(self, date, event_name):
        events = self._get_day_solar_event_dict(date)
        return events.get(event_name)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_day_solar_event_dict(self, date):
        return self._get_date_solar_event_dict(date, True)
    
    
    def _get_date_solar_event_dict(self, date, day):
        
        if day:
            events = self.get_day_solar_events(date)
        else:
            events = self.get_night_solar_events(date)
            
        return dict((e.name, e.time) for e in events)
    
        
    def get_night_solar_event_time(self, date, event_name):
        events = self._get_night_solar_event_dict(date)
        return events.get(event_name)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_night_solar_event_dict(self, date):
        return self._get_date_solar_event_dict(date, False)
    
    
    def get_solar_period_name(self, time):
        
        arg = self._get_skyfield_time(time)
        period_codes = self._solar_period_function(arg)
        
        if len(period_codes.shape) == 0:
            # getting period name for single time
            
            return _SOLAR_PERIOD_NAMES[float(period_codes)]
        
        else:
            # getting period names for list of times
            
            return [_SOLAR_PERIOD_NAMES(c) for c in period_codes]
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_lunar_position(self, time):
        return self._get_position(self._moon, time)
    
    
    def get_lunar_fraction_illuminated(self, time):
        t = self._get_skyfield_time(time)
        return almanac.fraction_illuminated(self._ephemeris, 'moon', t)


def _get_location(location):
    if isinstance(location, Location):
        return location
    else:
        return Location(
            location.latitude, location.longitude, location.time_zone)


def _check_time_zone_awareness(time):
    tzinfo = time.tzinfo
    if tzinfo is None or tzinfo.utcoffset(time) is None:
        raise ValueError('Time does not include a time zone.')


# TODO: Move this function to a utility module and use it more widely,
# as part of an effort to eventually eliminate the use of `pytz` in
# Vesper. `pytz` should not be needed for Python versions 3.9 and above,
# after the introduction of the `zoneinfo` standard library package.
def _create_aware_datetime(time_zone, *args):
    
    if hasattr(time_zone, 'localize'):
        
        # Here we assume that since `time_zone` has a `localize`
        # attribute it is a `pytz` time zone, and it is not safe to
        # use it as the `tzinfo` argument to the `datetime` initializer.
        # Instead, to create a localized `datetime` we first construct
        # a naive `datetime` and then localize that with the time zone's
        # `localize` method. See the "Localized times and date arithmetic"
        # section of the pytz documentation (pytz.sourceforge.net)
        # for more information.
        naive_dt = datetime.datetime(*args)
        return time_zone.localize(naive_dt)
    
    else:
        # time zone has no `localize` attribute
        
        # Here we assume that since `self.time_zone` does not have a
        # `localize` attribute it's safe to use it as the `tzinfo`
        # argument to the `datetime` initializer. This is the case,
        # for example, for `datetime.timezone` objects.
        return datetime.datetime(*args, tzinfo=time_zone)


def _filter_events(events, name_filter):
    
    if name_filter is None:
        return events
    
    elif isinstance(name_filter, str):
        return [e for e in events if e.name == name_filter]
    
    else:
        # name filter is neither `None` nor a string
        
        # We assume here that the name filter is an iterable of strings,
        # and create a `frozenset` of strings from it if it isn't a
        # `frozenset` already.
        
        if not isinstance(name_filter, frozenset):
            name_filter = frozenset(name_filter)
            
        return [e for e in events if e.name in name_filter]


def _get_solar_event_name(code_0, code_1):
    return _SOLAR_EVENT_NAMES[(code_0, code_1)]


def _discard_extra_events(events, day, transit_time):
    return [e for e in events if _retain_event(e, day, transit_time)]


def _retain_event(event, day, transit_time):
    
    name = event.name
    time = event.time
    
    if day:
        return not (
            _is_setting_event(name) and time < transit_time or
            _is_rising_event(name) and time > transit_time)
    
    else:
        return not (
            _is_rising_event(name) and time < transit_time or
            _is_setting_event(name) and time > transit_time)


def _is_rising_event(name):
    return name in _RISING_EVENT_NAMES


def _is_setting_event(name):
    return name in _SETTING_EVENT_NAMES


class AstronomicalCalculatorCache:
    
    
    """
    Astronomical calculator cache.
    
    An `AstronomicalCalculatorCache` maintains a cache of
    `AstronomicalCalculator` objects. Different functions that
    perform astronomical calculations for the same locations can
    share `AstronomicalCalculator` objects by getting them from
    the same calculator cache, thus accelerating their calculations.
    
    The `result_times_local` initializer argument determines whether
    the calculators of the cache return local times or UTC times.
    
    The `max_size` initializer argument determines the maximum
    number of calculators the cache will hold. Least recently
    used calculators are discarded as needed to keep the cache
    size from exceeding this limit.
    """
    
    
    DEFAULT_MAX_SIZE = 100
    
    
    def __init__(self, result_times_local=False, max_size=DEFAULT_MAX_SIZE):
        
        self._result_times_local = result_times_local
        
        self._calculators = LruCache(max_size)
        """
        `AstronomicalCalculator` cache.
        
        This class uses a (latitude, longitude, time_zone) tuple as a
        cache key instead of a `location` object so that a single
        calculator can be cached for several different `location` objects
        (even objects of different types) as long as they have the same
        latitude, longitude, and time zone.
        
        We use the `LruCache` class instead of the `functools.lru_cache`
        decorator to implement caching so we can make the cache size
        configurable via an initializer argument.
        """
    
    
    @property
    def result_times_local(self):
        return self._result_times_local
    
    
    @property
    def max_size(self):
        return self._calculators.max_size
    
    
    def get_calculator(self, location):
         
        key = (location.latitude, location.longitude, location.time_zone)
         
        try:
            return self._calculators[key]
         
        except KeyError:
            # cache miss
             
            calculator = AstronomicalCalculator(
                location, self.result_times_local)
             
            self._calculators[key] = calculator
             
            return calculator
