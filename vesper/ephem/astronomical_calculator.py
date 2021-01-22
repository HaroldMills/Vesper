"""Module containing class `AstronomicalCalculator`."""


from collections import namedtuple
from functools import lru_cache
from pathlib import Path
import datetime
import pytz

from skyfield import almanac
from skyfield.api import Topos, load, load_file

from vesper.util.lru_cache import LruCache


# TODO: Make time zone optional. When absent, use UTC-offset time zone.
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

_TWILIGHT_EVENT_NAMES = {
    (0, 1): 'Astronomical Dawn',
    (1, 2): 'Nautical Dawn',
    (2, 3): 'Civil Dawn',
    (3, 4): 'Sunrise',
    (4, 3): 'Sunset',
    (3, 2): 'Civil Dusk',
    (2, 1): 'Nautical Dusk',
    (1, 0): 'Astronomical Dusk'
}

_MORNING_TWILIGHT_EVENT_NAMES = frozenset((
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise'
))

_EVENING_TWILIGHT_EVENT_NAMES = frozenset((
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk'
))

_SUNLIGHT_PERIOD_NAMES = {
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

def __init__(self, latitude, longitude, time_zone, result_times_local=False)

@property
def latitude(self)

@property
def longitude(self)

@property
def time_zone(self)

@property
def result_times_local(self)

def get_solar_position(self, time)

def get_solar_noon(self, date)

def get_solar_midnight(self, date)

def get_twilight_events(self, start_time, end_time, event_names=None)

def get_day_twilight_events(self, date, event_names=None)

def get_day_twilight_event_time(self, date, event_name)

def get_night_twilight_events(self, date, event_names=None)

def get_night_twilight_event_time(self, date, event_name)

def get_sunlight_period_name(self, time)
    
def get_lunar_position(self, time)
    
def get_lunar_illumination(self, time)


Omit the following methods initially. Skyfield does not yet offer
moonrise and moonset calculations. It is more difficult to calculate
rise and set events for the moon than the sun because of the nearness
of the moon to the earth and the eccentricity of the moon's orbit.
These make the angle subtended by the moon more variable than the
angle subtended by the sun.

def get_lunar_rise_set_events(self, start_time, end_time, name_filter=None)

def is_moon_up(self, time)
'''


'''
Sunlight period definitions, with numbers in degrees:

Night: altitude < -18
Astronomical Twilight: -18 <= altitude < -12
Nautical Twilight: -12 <= altitude < -6
Civil Twilight: -6 <= altitude < -.833333
Day: altitude >= -8.33333

I have more or less arbitrarily chosen which ends of the intervals
are open and closed above. I don't know of any "official" (e.g. from
the US Naval Observatory) definitions that include that level of
detail. The boundary altitudes of -18, -12, -6, and -8.3_ (i.e 8
and one third) degrees are standard, however.
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


class AstronomicalCalculator:
    
    
    """
    Solar and lunar astronomical calculator for a single location.
    
    An `AstronomicalCalculator` calculates various quantities
    related to the observation of the sun and the moon from a
    particular location on the earth. The quantities include the
    positions of the sun and moon in the sky, the times of twilight
    events (like sunrise and sunset) defined in terms of the altitude
    of the sun, and the illuminated fraction of the moon.
    
    An `AstronomicalCalculator` performs all computations for an
    observer at sea level, since quantities computed at other
    (realistic, terrestrial) elevations seem to differ only very
    slightly from those. For example, sunrise times for observers
    at sea level and an elevation of 10,000 meters (i.e. higher
    than the top of Mount Everest) differ by only about a
    millisecond at the latitude and longitude of Ithaca, New York.
    
    The `latitude` and `longitude` initializer arguments specify
    the location for which the calculator should perform computations.
    They have units of degrees.
    
    The `time_zone` initializer argument specifies the local time
    zone of a calculator. It can be either a string IANA time zone
    name (e.g. "US/Eastern") or an instance of a `datetime.tzinfo`
    subclass, including a `pytz` time zone.
    
    The `result_times_local` initializer argument determines whether
    times returned by the methods of a calculator are in the local
    time zone or UTC.
    
    The time zone of an astronomical calculator is used for two
    purposes. First, if the `result_times_local` property of the
    calculator is `True`, the calculator uses the time zone to
    all times returned by its methods local.
    
    Second, all calculator methods that find events for a specified
    date use the time zone to help identify the correct UTC interval
    to search for the events. For most locations, including all those
    a sufficient longitudinal distance from the 180th meridian, the
    the correct interval can be found by a simple algorithm that
    assumes that that meridian is the international date line. The
    international date line is not simply that meridian, however, so
    the algorithm fails in some areas near it. In order to guarantee
    correct results for all locations on earth, we have chosen to
    simply require specification of a time zone for every astronomical
    calculator.
    
    A future version of this class may make time zones optional for
    calculators that don't need them, i.e. for calculators with
    locations for which the algorithm mentioned in the previous
    paragraph works, and that return UTC times instead of local ones.
    
    Methods that have `datetime` arguments require that those arguments
    be time-zone-aware.
    
    Several of the methods of this class cache results to improve the
    efficiency of repeated invocations with the same arguments. These
    methods are:
    
        * get_solar_position
        * get_solar_noon
        * get_solar_midnight
        * get_day_twilight_events
        * get_night_twilight_events
        * get_day_twilight_event_time
        * get_night_twilight_event_time
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
    
    
    def __init__(
            self, latitude, longitude, time_zone, result_times_local=False):
        
        AstronomicalCalculator._init_if_needed()
        
        self._latitude = latitude
        self._longitude = longitude
        self._time_zone = _get_time_zone(time_zone)
        self._result_times_local = result_times_local
        
        # See comment in class docstring about why we perform all
        # computations for an observer at zero elevation, i.e. at sea level.
        self._topos = Topos(
            latitude_degrees=self._latitude,
            longitude_degrees=self._longitude,
            elevation_m=0)
        
        self._loc = self._earth + self._topos
        
        self._solar_transit_function = \
            almanac.meridian_transits(self._ephemeris, self._sun, self._topos)
        
        self._sunlight_period_function = \
            almanac.dark_twilight_day(self._ephemeris, self._topos)
    
    
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
        self._check_for_polar_location('get solar noon')
        return self._get_solar_noon_or_midnight(date, True)
    
    
    def _check_for_polar_location(self, action):
        if abs(self.latitude) == 90:
            raise ValueError(f'Cannot {action} at a pole.')


    def _get_solar_noon_or_midnight(self, date, noon):
        
        # Get start hour of day and duration in hours of period that
        # includes desired solar noon or midnight. We use a period
        # from four hours before noon or midnight in the local time
        # zone to account for the full range of possible differences
        # between local clock time and local solar time all over the
        # earth.
        start_hour = 8 if noon else 20
        duration = 8
        
        # Note that this is the only place in this class where we
        # use the local time zone, except when we convert result
        # UTC times to local times. If we decide to make the time
        # zone optional, when we don't have it here we can use a
        # UTC-offset time zone instead, with the offset computed
        # assuming that the 180th meridian is the international
        # date line. That will work for most locations, except
        # those where the date differs from what it would be if
        # the 180th meridian were the international date line.
        local_start_time = _create_aware_datetime(
            self.time_zone, date.year, date.month, date.day,
            start_hour)
        
        start_time = self._timescale.from_datetime(local_start_time)
        
        local_end_time = local_start_time + datetime.timedelta(hours=duration)
        end_time = self._timescale.from_datetime(local_end_time)
        
        ts, _ = almanac.find_discrete(
            start_time, end_time, self._solar_transit_function)
        
        time = ts[0].utc_datetime()
        
        if self.result_times_local:
            time = time.astimezone(self.time_zone)
            
        return time
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_solar_midnight(self, date):
        self._check_for_polar_location('get solar midnight')
        return self._get_solar_noon_or_midnight(date, False)
           
    
    def get_twilight_events(self, start_time, end_time, name_filter=None):
        
        # Get start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_time)
        end_time = self._get_scalar_skyfield_time(end_time)
        
        # Get twilight event times and codes.
        times, codes = almanac.find_discrete(
            start_time, end_time, self._sunlight_period_function)
        
        # Get event times as UTC `datetime` objects.
        times = [t.utc_datetime() for t in times]
        
        # Convert event times from UTC to local time zone if needed.
        if self.result_times_local:
            time_zone = self.time_zone
            times = [time.astimezone(time_zone) for time in times]

        # Get event names.
        names = self._get_twilight_event_names(times, codes)
        
        # Create event named tuples.
        events = [Event(time, name) for time, name in zip(times, names)]
        
        # Filter events by name if needed.
        events = _filter_events(events, name_filter)
        
        return events
    
    
    def _get_twilight_event_names(self, times, codes):
        
        event_count = len(codes)
        
        if event_count == 0:
            return []
        
        else:
            # have at least one event
            
            first_event_name = \
                self._get_first_twilight_event_name(times[0], codes[0])
            
            other_event_names = [
                _get_twilight_event_name(codes[i], codes[i + 1])
                for i in range(event_count - 1)]
            
            return [first_event_name] + other_event_names
            
            
    def _get_first_twilight_event_name(self, time, code):
        
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
            
            
    def get_day_twilight_events(self, date, name_filter=None):
        self._check_for_polar_location('get day twilight events')
        events = self._get_day_twilight_events(date)
        return _filter_events(events, name_filter)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_day_twilight_events(self, date):
        return self._get_date_twilight_events(date, True)
    
    
    def _get_date_twilight_events(self, date, day):
        
        """
        Gets twilight events for the specified day or night.
        
        The `_get_day_twilight_events` and `_get_night_twilight_events`
        methods both call this one, the `_get_day_twilight_events` method
        to get twilight events that occur between one solar midnight and
        the next, and the `_get_night_twilight_events` method to get events
        that occur between one solar noon and the next. In both cases,
        there is at most one event of each event type during the relevant
        time interval. Some or all events do not occur at higher latitudes
        for some days, e.g. during the summer and winter.
        
        We rely on Skyfield to find twilight event times. It can tell us
        the times and types of events that occur during any specified
        time interval. In order to avoid losing events due to edge
        effects, when searching for day twilight events we do not simply
        search for the events from one solar midnight to the next,
        but rather for the events in an expanded time interval that
        extends from about an hour before the first solar midnight to
        about an hour after the second one. When searching for night
        twilight events, we expand the search interval analogously,
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
        events = self.get_twilight_events(start_time, end_time)
        
        # Discard extra events (see docstring for this method for more).
        events = _discard_extra_events(events, day, transit_time)
        
        return events
    
    
    def get_night_twilight_events(self, date, name_filter=None):
        self._check_for_polar_location('get night twilight events')
        events = self._get_night_twilight_events(date)
        return _filter_events(events, name_filter)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_night_twilight_events(self, date):
        return self._get_date_twilight_events(date, False)
    
    
    def get_day_twilight_event_time(self, date, event_name):
        self._check_for_polar_location('get day twilight event time')
        events = self._get_day_twilight_event_dict(date)
        return events.get(event_name)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_day_twilight_event_dict(self, date):
        return self._get_date_twilight_event_dict(date, True)
    
    
    def _get_date_twilight_event_dict(self, date, day):
        
        if day:
            events = self.get_day_twilight_events(date)
        else:
            events = self.get_night_twilight_events(date)
            
        return dict((e.name, e.time) for e in events)
    
        
    def get_night_twilight_event_time(self, date, event_name):
        self._check_for_polar_location('get night twilight event time')
        events = self._get_night_twilight_event_dict(date)
        return events.get(event_name)
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def _get_night_twilight_event_dict(self, date):
        return self._get_date_twilight_event_dict(date, False)
    
    
    def get_sunlight_period_name(self, time):
        
        """
        Gets the name of the sunlight period that includes the specified time.
        
        The possible return values are:
        
            Night
            Morning Astronomical Twilight
            Morning Nautical Twilight
            Morning Civil Twilight
            Day
            Evening Civil Twilight
            Evening Nautical Twilight
            Evening Astronomical Twilight
 
        By definition, morning twilight occurs between solar midnight
        and the following solar noon, when the sun's altitude is
        increasing. Evening twilight occurs between solar noon and the
        following solar midnight, when the sun's altitude is decreasing.
        
        Note that at sufficiently high latitudes, a night may have just
        one civil, nautical, or astronomical twilight period if the
        sun's altitude remains sufficiently low. Such a twilight period
        still has evening and morning portions, however (unless the
        period comprises a single point, solar midnight), with the
        evening portion prior to and the morning portion beginning at
        solar midnight.
        """
        
        self._check_for_polar_location('get sunlight period name')

        arg = self._get_skyfield_time(time)
        period_codes = self._sunlight_period_function(arg)
        
        if len(period_codes.shape) == 0:
            # getting period name for single time
            
            return self._get_sunlight_period_name(period_codes, time)
        
        else:
            # getting period names for list of times
            
            return [
                self._get_sunlight_period_name(c, time)
                for c in period_codes]
    
    
    def _get_sunlight_period_name(self, code, time):
        
        code = float(code)
        
        name = _SUNLIGHT_PERIOD_NAMES[code]
        
        if name == 'Day' or name == 'Night':
            return name
        
        else:
            # some kind of twilight
            
            # Get solar midnight of solar night that includes `time`.
            # If `time` is before the solar noon of its day, the relevant
            # solar midnight is the one that precedes that solar noon.
            # Otherwise it's the one after. This solar midnight always
            # separates the evening and morning twilight periods.
            date = time.date()
            noon = self.get_solar_noon(date)
            if time < noon:
                date = date - _ONE_DAY
            midnight = self.get_solar_midnight(date)
            
            prefix = 'Evening' if time < midnight else 'Morning'
            
            return f'{prefix} {name}'
    
    
    @lru_cache(_MAX_CACHE_SIZE)
    def get_lunar_position(self, time):
        return self._get_position(self._moon, time)
    
    
    def get_lunar_illumination(self, time):
        t = self._get_skyfield_time(time)
        return almanac.fraction_illuminated(self._ephemeris, 'moon', t)


def _get_time_zone(time_zone):
    
    if time_zone is None:
        return None
    
    elif isinstance(time_zone, str):
        return pytz.timezone(time_zone)
    
    elif isinstance(time_zone, datetime.tzinfo):
        return time_zone
    
    else:
        raise TypeError(
            f'Unrecognized time zone type "{time_zone.__class__.__name__}".'
            f'Time zone must be string, tzinfo, or None.')


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


def _get_twilight_event_name(code_0, code_1):
    return _TWILIGHT_EVENT_NAMES[(code_0, code_1)]


def _discard_extra_events(events, day, transit_time):
    return [e for e in events if _retain_event(e, day, transit_time)]


def _retain_event(event, day, transit_time):
    
    name = event.name
    time = event.time
    
    if day:
        return not (
            _is_evening_event(name) and time < transit_time or
            _is_morning_event(name) and time > transit_time)
    
    else:
        return not (
            _is_morning_event(name) and time < transit_time or
            _is_evening_event(name) and time > transit_time)


def _is_morning_event(name):
    return name in _MORNING_TWILIGHT_EVENT_NAMES


def _is_evening_event(name):
    return name in _EVENING_TWILIGHT_EVENT_NAMES


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
    
    
    def get_calculator(self, latitude, longitude, time_zone):
        
        """
        Gets a calculator for the specified latitude, longitude, and
        time zone.
        
        The `latitude` and `longitude` arguments specify the location
        of the desired calculator. They have units of degrees.
        
        The `time_zone` argument specifies the local time zone at the
        calculator's location.
        
        Note that a calculator stores calculators according to their
        locations, but not their time zones. The time zone of a
        calculator is used only to construct it, the first time this
        method is called for the calculator's location. The time
        zone is ignored in subsequent calls.
        """
        
        key = (latitude, longitude)
        
        try:
            return self._calculators[key]
        
        except KeyError:
            # cache miss
            
            calculator = AstronomicalCalculator(
                latitude, longitude, time_zone, self.result_times_local)
            
            self._calculators[key] = calculator
            
            return calculator
