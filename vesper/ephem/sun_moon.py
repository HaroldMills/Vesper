"""Module containing class `SunMoon`."""


from collections import namedtuple
from datetime import (
    datetime as DateTime,
    timedelta as TimeDelta,
    tzinfo as TzInfo)
from pathlib import Path
import heapq

from skyfield import almanac
from skyfield.api import Topos, load, load_file
import pytz

from vesper.util.lru_cache import LruCache


# TODO: Consider how much of a problem it is to define solar noon and
# midnight in terms of meridian and antimeridian transits instead of
# altitude extrema. The two are close (how close?) but not identical
# (see https://rhodesmill.org/skyfield/almanac.html#transits for more).
# Defining solar noon and midnight in terms of transits can cause
# certain problems in rare (how rare?) circumstances, such as an
# astronomical dawn for a day that slightly precedes the midnight that
# starts that day. We could avoid such problems by defining solar noon
# and midnight in terms of altitude extrema instead of transits. That
# would be more expensive (how much?) computationally, however. Is it
# worth the expense to avoid rare oddities?

# TODO: Make time zone optional. When absent, return only UTC times
# from methods, raising an exception if local result times are
# indicated to the initializer, and use a UTC-offset time zone
# internally when a time zone is required for computations. Compute
# the UTC offset from the longitude, assuming that the 180th
# meridian is the international date line. That will work for most
# locations on the earth, except those where the actual date differs
# from what it would be if the 180th meridian were the international
# date line.


_EPHEMERIS_FILE_PATH = Path(__file__).parent / 'data' / 'de421.bsp'
"""
Jet Propulsion Laboratory Development Ephemeris (JPL DE) Spice Planet
Kernel (SPK) file path. See
en.wikipedia.org/wiki/Jet_Propulsion_Laboratory_Development_Ephemeris
for a discussion of the JPL DE.

See https://pypi.org/project/jplephem/ for instructions on excerpting
SPK files. This might be a good idea to reduce the SPK file size.
"""

_TWILIGHT_EVENT_NAMES = (
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise',
    'Sunset',
    'Civil Dusk',
    'Nautical Dusk',
    'Astronomical Dusk',
)

_TWILIGHT_EVENT_NAME_SET = frozenset(_TWILIGHT_EVENT_NAMES)

_TWILIGHT_EVENT_CODE_PAIRS = (
    (0, 1),  # Astronomical Dawn
    (1, 2),  # Nautical Dawn
    (2, 3),  # Civil Dawn
    (3, 4),  # Sunrise
    (4, 3),  # Sunset
    (3, 2),  # Civil Dusk
    (2, 1),  # Nautical Dusk
    (1, 0),  # Astronomical Dusk
)

_TWILIGHT_EVENT_NAME_DICT = dict(
    zip(_TWILIGHT_EVENT_CODE_PAIRS, _TWILIGHT_EVENT_NAMES))

_SOLAR_TRANSIT_EVENT_NAMES = ('Solar Midnight', 'Solar Noon')

_SOLAR_TRANSIT_EVENT_NAME_SET = frozenset(_SOLAR_TRANSIT_EVENT_NAMES)

_MORNING_SOLAR_EVENT_NAMES = frozenset((
    'Astronomical Dawn',
    'Nautical Dawn',
    'Civil Dawn',
    'Sunrise'
))

_SOLAR_PERIOD_NAMES = {
    0: 'Night',
    1: 'Astronomical Twilight',
    2: 'Nautical Twilight',
    3: 'Civil Twilight',
    4: 'Day'
}

_ONE_HOUR = TimeDelta(hours=1)
_ONE_DAY = TimeDelta(days=1)


'''
SunMoon methods:

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

def get_solar_events_in_interval(self, start_time, end_time, event_names=None)

def get_solar_date(self, time, day=True)

def get_solar_events(self, date, event_names=None, day=True)

def get_solar_event_time(self, date, event_name, day=True)

def get_solar_period_name(self, time)

def get_lunar_position(self, time)
    
def get_lunar_illumination(self, time)


event_names = ('Solar Midnight', 'Solar Noon')
events = sun_moon.get_solar_events(date, event_names)

Omit the following methods initially. Skyfield does not yet offer
moonrise and moonset calculations. It is more difficult to calculate
rise and set events for the moon than the sun because of the nearness
of the moon to the earth and the eccentricity of the moon's orbit.
These make the angle subtended by the moon more variable than the
angle subtended by the sun.

def get_lunar_events_in_interval(self, start_time, end_time, event_names=None)

def get_lunar_events(self, date, event_names=None, day=True)

def get_lunar_event_time(self, date, event_name, day=True)

def is_moon_up(self, time)


Solar event names:

    Solar Midnight
    Astronomical Dawn
    Nautical Dawn
    Civil Dawn
    Sunrise
    Solar Noon
    Sunset
    Civil Dusk
    Nautical Dusk
    Astronomical Dusk
    
Lunar event names:

    Moonrise
    Moonset
'''


'''
Solar period definitions, with numbers in degrees:

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


class SunMoon:
    
    """
    Solar and lunar astronomical calculator for a single location.
    
    A `SunMoon` calculates various quantities related to the observation
    of the sun and the moon from a particular location on the earth. The
    quantities include the positions of the sun and moon in the sky, the
    times of solar events (like sunrise and sunset) defined in terms of
    the altitude of the sun, and the illuminated fraction of the moon.
    
    A `SunMoon` performs all computations for an observer at sea level,
    since quantities computed at other (realistic, terrestrial) elevations
    seem to differ only very slightly from those. For example, sunrise
    times for observers at sea level and an elevation of 10,000 meters
    (i.e. higher than the top of Mount Everest) differ by only about a
    millisecond at the latitude and longitude of Ithaca, New York.
    
    The `latitude` and `longitude` initializer arguments specify
    the location for which the `SunMoon` should perform computations.
    They have units of degrees.
    
    The `time_zone` initializer argument specifies the local time zone
    of a `SunMoon`. It can be either a string IANA time zone name (e.g.
    "US/Eastern") or an instance of a `datetime.tzinfo` subclass,
    including a `pytz` time zone.
    
    The `result_times_local` initializer argument determines whether
    times returned by the methods of a `SunMoon` are in the local time
    zone or UTC.
    
    The time zone of a `SunMoon` is used for two purposes. First, if
    the `result_times_local` property of the object is `True`, the
    object uses the time zone to make all times returned by its methods
    local.
    
    Second, all `SunMoon` methods that find events for a specified
    date use the time zone to help identify the correct UTC interval
    to search for the events. For most locations, including all those
    a sufficient longitudinal distance from the 180th meridian, the
    the correct interval can be found by a simple algorithm that
    assumes that that meridian is the international date line. The
    international date line is not simply that meridian, however, so
    the algorithm fails in some areas near it. In order to guarantee
    correct results for all locations on earth, we have chosen to
    simply require specification of a time zone for every `SunMoon`
    object.
    
    A future version of this class may make time zones optional for
    `SunMoon` objects that don't need them, i.e. for objects with
    locations for which the algorithm mentioned in the previous
    paragraph works, and that return UTC times instead of local ones.
    
    Methods that have `datetime` arguments require that those arguments
    be time-zone-aware.
    
    Several of the methods of this class cache results to improve the
    efficiency of repeated invocations with the same arguments. These
    methods are:
    
        * get_solar_position
        * get_solar_events
        * _get_solar_transit_events
        * get_solar_event_time
        * get_lunar_position
    """
    
    
    TWILIGHT_EVENT_NAMES = _TWILIGHT_EVENT_NAMES
    
    SOLAR_TRANSIT_EVENT_NAMES = _SOLAR_TRANSIT_EVENT_NAMES
    
    SOLAR_EVENT_NAMES = tuple(sorted(
        TWILIGHT_EVENT_NAMES + SOLAR_TRANSIT_EVENT_NAMES))
    
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
        
        SunMoon._init_if_needed()
        
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
        
        self._solar_period_function = \
            almanac.dark_twilight_day(self._ephemeris, self._topos)
        
        # Caches for data returned by various methods of this class.
        # We use per-instance `LruCache` objects instead of decorating
        # the methods with `@functools.lrucache` since the former gives
        # each instance its own private set of caches, while the latter
        # shares one set of caches across all instances.
        self._solar_positions = LruCache(self._MAX_CACHE_SIZE)
        self._solar_transit_events = LruCache(self._MAX_CACHE_SIZE)
        self._solar_events = LruCache(self._MAX_CACHE_SIZE)
        self._solar_event_dicts = LruCache(self._MAX_CACHE_SIZE)
        self._lunar_positions = LruCache(self._MAX_CACHE_SIZE)
    
    
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
    
    
    def get_solar_position(self, time):
        return self._get_position(self._solar_positions, self._sun, time)
    
    
    def _get_position(self, cache, body, time):
        if isinstance(time, DateTime):
            return self._get_scalar_position(cache, body, time)
        else:
            return self._get_vector_position(body, time)
    
    
    def _get_scalar_position(self, cache, body, time):
        
        try:
            return cache[time]
 
        except KeyError:
            # cache miss
            
            time = self._get_scalar_skyfield_time(time)
            position = self._loc.at(time).observe(body).apparent().altaz()
            position = _get_sun_moon_position(position)
            
            cache[time] = position
            
            return position
    
    
    def _get_scalar_skyfield_time(self, time):
        _check_time_zone_awareness(time)
        return self._timescale.from_datetime(time)
    
    
    def _get_vector_position(self, body, times):
        
        # Note that unlike in the scalar case, we do not cache results
        # when getting a vector of positions.
        
        times = self._get_vector_skyfield_time(times)
        position = self._loc.at(times).observe(body).apparent().altaz()
        return _get_sun_moon_position(position)
    
    
    def _get_vector_skyfield_time(self, times):
        
        # Create `list` from iterable `times` since the documentation
        # for the Skyfield `Timescale.from_datetimes` method specifies
        # that its argument should be a list of `DateTime` objects.
        times = list(times)
        
        for time in times:
            _check_time_zone_awareness(time)
        
        return self._timescale.from_datetimes(times)
    
    
    def _check_for_polar_location(self, action):
        if abs(self.latitude) == 90:
            raise ValueError(f'Cannot {action} at a pole.')
    
    
    def get_solar_events_in_interval(
            self, start_time, end_time, name_filter=None):
        
        # Get start and end times of search interval.
        search_start_time = start_time - _ONE_HOUR
        search_end_time = end_time + _ONE_HOUR
        
        # Get search start and end times as Skyfield `Time` objects.
        search_start_time = self._get_scalar_skyfield_time(search_start_time)
        search_end_time = self._get_scalar_skyfield_time(search_end_time)
        
        name_filter, twilight_events_included, transit_events_included = \
            _normalize_solar_event_name_filter(name_filter)
        
        # Get twilight events.
        if twilight_events_included:
            twilight_events = self._get_events(
                search_start_time, search_end_time,
                self._solar_period_function, self._get_twilight_event_names,
                name_filter)
        else:
            twilight_events = []
        
        # Get transit events.
        if transit_events_included:
            transit_events = self._get_events(
                search_start_time, search_end_time,
                self._solar_transit_function,
                self._get_solar_transit_event_names, name_filter)
        else:
            transit_events = []
        
        # Merge twilight and transit events.
        if len(twilight_events) != 0 and len(transit_events) != 0:
            events = list(heapq.merge(twilight_events, transit_events))
        else:
            events = twilight_events + transit_events
        
        # Discard events outside of requested time interval.
        events = _discard_extra_events(events, start_time, end_time)
        
        return events
    
    
    def _get_events(
            self, start_time, end_time, period_getter, event_name_getter,
            name_filter=None):
        
        # Get event times and codes.
        times, codes = almanac.find_discrete(
            start_time, end_time, period_getter)
        
        # Get event times as UTC `datetime` objects.
        times = [t.utc_datetime() for t in times]
        
        # Convert event times from UTC to local time zone if needed.
        if self.result_times_local:
            time_zone = self.time_zone
            times = [time.astimezone(time_zone) for time in times]
        
        # Get event names.
        names = event_name_getter(times, codes)
        
        # Create event named tuples.
        events = [Event(time, name) for time, name in zip(times, names)]
        
        # Filter events by name if needed.
        events = _filter_events(events, name_filter)
        
        return events
    
    
    def _get_solar_transit_event_names(self, times, codes):
        return [_SOLAR_TRANSIT_EVENT_NAMES[code] for code in codes]
    
    
    def _get_twilight_event_names(self, times, codes):
        
        event_count = len(codes)
        
        if event_count == 0:
            return []
        
        else:
            # have at least one event
            
            first_event_name = \
                self._get_first_twilight_event_name(times[0], codes[0])
            
            other_event_names = [
                _TWILIGHT_EVENT_NAME_DICT[(codes[i], codes[i + 1])]
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
    
    
    def get_solar_date(self, time, day=True):
        
        self._check_for_polar_location('get solar date')
        
        if isinstance(time, DateTime):
            return self._get_solar_date(time, day)
 
        else:
            # `time` is not a `DateTime`
            
            # Asume `time` is a `DateTime` iterable.
            
            return [self._get_solar_date(t, day) for t in time]
    
    
    def _get_solar_date(self, time, day):
        
        # Get calendar date of `time`.
        date = time.date()
        
        # Get start and end transit events for the solar day or night
        # of `date`.
        start, _, end = self._get_solar_transit_events(date, day)
        
        if time < start.time:
            # `time` precedes solar day or night of `date`.
            
            return date - _ONE_DAY
        
        elif time < end.time:
            # `time` is during solar day or night of `date`.
            return date
        
        else:
            # `time` follows solar day or night of `date`.
            
            return date + _ONE_DAY
    
    
    def get_solar_events(self, date, name_filter=None, day=True):
        
        self._check_for_polar_location('get solar events')
        
        name_filter, twilight_events_included, _ = \
            _normalize_solar_event_name_filter(name_filter)
            
        if twilight_events_included:
            events = self._get_solar_events(date, day)
            
        else:
            # result will contain only transit events
            
            # Get three transit events for the specified day or night,
            # one at the beginning, one in the middle, and one at the
            # end.
            events = self._get_solar_transit_events(date, day)
            
            # Discard third transit event. This event is either the
            # solar midnight at the end of the specified day or the
            # solar noon at the end of the specified night. The
            # `_get_solar_transit_events` method returns these events
            # since we use them elsewhere, but we don't want them here.
            events = events[:2]
        
        events = _filter_events(events, name_filter)
        
        return events
    
    
    def _get_solar_events(self, date, day):
        
        key = (date, day)
        
        try:
            return self._solar_events[key]
        
        except KeyError:
            # cache miss
            
            events = self._get_solar_events_aux(date, day)
            self._solar_events[key] = events
            return events
    
    
    def _get_solar_events_aux(self, date, day):
        
        # Get solar transit events for the specified solar day or
        # night. This yields exactly three events. For a day, the
        # events are the starting and ending midnight and the noon
        # between them. For a night, the events are the starting and
        # ending noon and the midnight between them.
        transit_events = self._get_solar_transit_events(date, day)
        
        # Get start and end UTC times of twilight event search
        # interval. We search an interval that starts an hour before
        # the start of the relevant day or night and ends an hour
        # after the end of the day or night to avoid the possibility
        # of missing events due to edge effects. After the search, we
        # discard any extra events found that are outside of the
        # relevant day or night.
        start_time = transit_events[0].time - _ONE_HOUR
        end_time = transit_events[2].time + _ONE_HOUR
        
        # Get search start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_time)
        end_time = self._get_scalar_skyfield_time(end_time)
        
        # Get twilight events.
        twilight_events = self._get_events(
            start_time, end_time, self._solar_period_function,
            self._get_twilight_event_names)
        
        twilight_events = _discard_extra_twilight_events(
            twilight_events, transit_events[1], day)
        
        # Discard third transit event. We used the third transit event
        # above to establish the end time of the twilight event search
        # interval, but it is never included in the returned events.
        transit_events = transit_events[:2]
        
        # Merge twilight and transit events in order of increasing time.
        events = list(heapq.merge(twilight_events, transit_events))
        
        return events
    
    
    def _get_solar_transit_events(self, date, day):
        
        key = (date, day)
        
        try:
            return self._solar_transit_events[key]
        
        except KeyError:
            # cache miss
            
            events = self._get_solar_transit_events_aux(date, day)
            self._solar_transit_events[key] = events
            return events
    
    
    def _get_solar_transit_events_aux(self, date, day):
        
        # Get start of time interval to search for solar transit events
        # as offset from local civil midnight of specified date.
        start_offset = TimeDelta(hours=-4 if day else 8)
        
        # Get duration of time interval to search for solar transit events.
        duration = TimeDelta(hours=32)
        
        # Get local civil midnight of specified date.
        #
        # Note that this is the only place in this class where we
        # use the local time zone, except when we convert result
        # UTC times to local times. If we decide to make the time
        # zone of a `SunMoon` optional, when we don't have it here
        # we can use a UTC-offset time zone instead, with the offset
        # computed assuming that the 180th meridian is the
        # international date line. That will work for most locations,
        # excepting those where the date differs from what it would be
        # if the 180th meridian were the international date line.
        civil_midnight = _create_aware_datetime(
            self.time_zone, date.year, date.month, date.day)
        
        # Get search interval bounds as civil times.
        start_time = civil_midnight + start_offset
        end_time = start_time + duration
        
        # Get search interval bounds as Skyfield `Time` objects.
        start_time = self._timescale.from_datetime(start_time)
        end_time = self._timescale.from_datetime(end_time)
        
        # Get solar transit events.
        events = self._get_events(
            start_time, end_time, self._solar_transit_function,
            self._get_solar_transit_event_names)
        
        # Check that we got the expected number of events.
        assert len(events) == 3
        
        return events
    
    
    def get_solar_event_time(self, date, event_name, day=True):
        self._check_for_polar_location('get solar event time')
        events = self._get_solar_event_dict(date, day)
        return events.get(event_name)
    
    
    def _get_solar_event_dict(self, date, day):
        
        key = (date, day)
        
        try:
            return self._solar_event_dicts[key]
        
        except KeyError:
            # cache miss
            
            events = self.get_solar_events(date, day=day)
            events = dict((e.name, e.time) for e in events)
            self._solar_event_dicts[key] = events
            return events
    
    
    def get_solar_period_name(self, time):
        
        """
        Gets the name of the solar period that includes the specified time.
        
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
        
        self._check_for_polar_location('get solar period name')

        arg = self._get_skyfield_time(time)
        period_codes = self._solar_period_function(arg)
        
        if len(period_codes.shape) == 0:
            # getting period name for single time
            
            return self._get_solar_period_name(period_codes, time)
        
        else:
            # getting period names for iterable of times
            
            return [
                self._get_solar_period_name(c, t)
                for c, t in zip(period_codes, time)]
    
    
    def _get_skyfield_time(self, arg):
        
        if isinstance(arg, DateTime):
            return self._get_scalar_skyfield_time(arg)
            
        else:
            # `arg` is not a `DateTime`.
            
            # Assume `arg` is iterable of `DateTime` objects.
            
            return self._get_vector_skyfield_time(arg)
    
    
    def _get_solar_period_name(self, code, time):
        
        code = float(code)
        
        name = _SOLAR_PERIOD_NAMES[code]
        
        if name == 'Day' or name == 'Night':
            return name
        
        else:
            # some kind of twilight
            
            prefix = self._get_morning_or_evening(time)
            
            return f'{prefix} {name}'
    
    
    def _get_morning_or_evening(self, time):
        
        """
        Return whether it's morning or evening at the specified time.
        
        At any non-polar location (i.e. any location at which the
        notion of a solar day makes sense), we define *morning* as the
        portion of a solar day during which the sun is either rising or
        at its minimum altitude at the start of the dayg. We define
        evening as the rest of the day, i.e. the portion of the day
        during which the sun is either falling or at its maximum
        altitude.
        
        At any time at which there is not a solar altitude extremum,
        in any sufficiently small neighborhood of the time the sun's
        altitude will strictly increase or decrease according to
        whether the time is in the morning or the evening, respectively.
        We use this fact as the basis of the algorithm of this method.
        
        The method starts by comparing the sun's altitude at the
        specified time to its altitude one second before and after.
        If those three altitudes are strictly increasing or decreasing,
        the method concludes that it is morning or evening at the time,
        respectively. Otherwise it zooms in to a smaller neighborhood
        and repeats the test. It zooms in and repeats the test up to
        six times, after which it concludes that the time is very close
        to a solar extremum and assigns it to morning or evening
        according to the sun's altitude a second after.
        """
        
        
        # TODO: This method can yield an incorrect answer, for example
        # in some cases where `time` is less than a microsecond from an
        # altitude extremum, and perhaps also where the altitude function
        # is relatively flat, e.g. at higher latitudes. Characterize better
        # the conditions under which this happens and how large errors can
        # be, for example as a function of latitude. Improve the algorithm
        # if needed, and perhaps raise an exception in certain dangerous
        # territories, e.g. at very high latitudes.
        
        altitude = self.get_solar_position(time).altitude
        
        delta = 1
        
        for _ in range(7):
            
            td = TimeDelta(seconds=delta)
            
            altitude_before = self.get_solar_position(time - td).altitude
            delta_before = altitude - altitude_before
            
            altitude_after = self.get_solar_position(time + td).altitude
            delta_after = altitude_after - altitude
            
            if delta_before > 0 and delta_after > 0:
                # altitude increasing at `time`
                
                return 'Morning'
            
            elif delta_before < 0 and delta_after < 0:
                # altitude decreasing at `time`
                
                return 'Evening'
            
            else:
                
                # Zoom in.
                delta *= .1
        
        # If we get here, altitude is not strictly increasing or
        # decreasing from about one microsecond before `time` to
        # about one microsecond after. We are very close in time
        # to an altitude extremum.
        
        td = TimeDelta(seconds=1)
        altitude_after = self.get_solar_position(time + td).altitude
        delta_after = altitude_after - altitude
        
        if delta_after > 0:
            # sun rises from `time` to one second after
            
            # Note that `time` may actually be a little before an
            # altitude maximum here, in which case we return an
            # incorrect answer.
            return 'Morning'
        
        else:
            # sun falls from `time` to one second after
            
            # Note that `time` may actually be a little after an
            # altitude minimum here, in which case we return an
            # incorrect answer.
            return 'Evening'
    
    
    # The following is an older version of the `_get_solar_period_name`
    # method. It assumes that solar noons and midnights coincide with
    # altitude maxima and minima, which is nearly but not exactly true.
    # See https://rhodesmill.org/skyfield/almanac.html#transits for more
    # about that issue. (By how much do they differ? It would be
    # informative to plot a distribution of differences over a year for
    # a given latitude.)
#     def _get_solar_period_name(self, code, time):
#         
#         code = float(code)
#         
#         name = _SOLAR_PERIOD_NAMES[code]
#         
#         if name == 'Day' or name == 'Night':
#             return name
#         
#         else:
#             # some kind of twilight
#             
#             # Get date of local time.
#             time = time.astimezone(self.time_zone)
#             date = time.date()
#             
#             # Get start solar midnight, solar noon, and end solar midnight
#             # for date.
#             start_midnight, noon, end_midnight = \
#                 self._get_solar_transit_events(date, True)
#             
#             # Get twilight name prefix according to whether time is
#             # in a morning interval between a solar midnight and a
#             # solar noon or an evening interval between a solar noon
#             # and a solar midnight.
#             #
#             # We assume here that transits and altitude extrema coincide.
#             # See TODO towards the top of this module regarding this
#             # assumption.
#             if time < start_midnight.time:
#                 prefix = 'Evening'
#                 
#             elif time < noon.time:
#                 prefix = 'Morning'
#             
#             elif time < end_midnight.time:
#                 prefix = 'Evening'
#             
#             else:
#                 prefix = 'Morning'
#                         
#             return f'{prefix} {name}'
    
    
    def get_lunar_position(self, time):
        return self._get_position(self._lunar_positions, self._moon, time)
    
    
    def get_lunar_illumination(self, time):
        t = self._get_skyfield_time(time)
        return almanac.fraction_illuminated(self._ephemeris, 'moon', t)


def _get_time_zone(time_zone):
    
    if time_zone is None:
        return None
    
    elif isinstance(time_zone, str):
        return pytz.timezone(time_zone)
    
    elif isinstance(time_zone, TzInfo):
        return time_zone
    
    else:
        raise TypeError(
            f'Unrecognized time zone type "{time_zone.__class__.__name__}".'
            f'Time zone must be string, tzinfo, or None.')


def _get_sun_moon_position(position):
    
    """Converts a Skyfield position object to a `Position`."""
    
    # Get position attributes with desired units.
    altitude = position[0].degrees
    azimuth = position[1].degrees
    distance = position[2].km
    
    return Position(altitude, azimuth, distance)


def _check_time_zone_awareness(time):
    tzinfo = time.tzinfo
    if tzinfo is None or tzinfo.utcoffset(time) is None:
        raise ValueError('Time does not include a time zone.')


# TODO: Move this function to a utility module and use it more widely,
# as part of an effort to eventually eliminate the use of `pytz` in
# Vesper. `pytz` should not be needed for Python versions 3.9 and above,
# which include the `zoneinfo` standard library package.
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
        naive_dt = DateTime(*args)
        return time_zone.localize(naive_dt)
    
    else:
        # time zone has no `localize` attribute
        
        # Here we assume that since `self.time_zone` does not have a
        # `localize` attribute it's safe to use it as the `tzinfo`
        # argument to the `datetime` initializer. This is the case,
        # for example, for `datetime.timezone` objects.
        return DateTime(*args, tzinfo=time_zone)


def _normalize_solar_event_name_filter(name_filter):
    
    if name_filter is None:
        # no name filter
        
        twilight_events_included = True
        transit_events_included = True
    
    elif isinstance(name_filter, str):
        # name filter is single event name
        
        twilight_events_included = name_filter in _TWILIGHT_EVENT_NAME_SET
        transit_events_included = name_filter in _SOLAR_TRANSIT_EVENT_NAMES
    
    else:
        # name filter is neither `None` nor string
        
        # We assume that the name filter is an event name iterable.
        
        # If name filter is not already a `frozenset`, make it one.
        if not isinstance(name_filter, frozenset):
            name_filter = frozenset(name_filter)
            
        twilight_events_included = False
        transit_events_included = False
        
        for name in name_filter:
            
            if name in _TWILIGHT_EVENT_NAME_SET:
                twilight_events_included = True
                
            elif name in _SOLAR_TRANSIT_EVENT_NAMES:
                transit_events_included = True
    
    return name_filter, twilight_events_included, transit_events_included


def _discard_extra_events(events, start_time, end_time):
    
    if len(events) != 0:
        
        # Find index of first event whose time is at least `start_time`.
        start_index = 0
        while events[start_index].time < start_time:
            start_index += 1
        
        # Find index of first event whose time exceeds `end_time`.
        end_index = len(events)
        while events[end_index - 1].time > end_time:
            end_index -= 1
        
        events = events[start_index:end_index]
    
    return events


def _filter_events(events, name_filter):
    
    if name_filter is None:
        return events
    
    elif isinstance(name_filter, str):
        return [e for e in events if e.name == name_filter]
    
    else:
        # name filter is `frozenset` of event names
        
        return [e for e in events if e.name in name_filter]


def _discard_extra_twilight_events(events, transit_event, day):
    return [
        e for e in events
        if not _is_extra_twilight_event(e, transit_event, day)]


def _is_extra_twilight_event(event, transit_event, day):
    
    is_morning_event = event.name in _MORNING_SOLAR_EVENT_NAMES
    
    if day:
        # event is for a day, transit event is solar noon
        
        time_after_noon = event.time - transit_event.time
        
        if is_morning_event:
            
            # A morning event for a day will almost always be before
            # solar noon, and can never be more than a tiny bit after.
            # An extra morning event will be hours after.
            return time_after_noon >= _ONE_HOUR
        
        else:
            # evening event
            
            # An evening event for a day will almost always be after
            # solar noon, and can never be more than a tiny bit before.
            # An extra morning event will be hours before.
            return time_after_noon <= -_ONE_HOUR
    
    else:
        # event is for a night, transiv event is solar midnight
        
        time_after_midnight = event.time - transit_event.time
        
        if is_morning_event:
            
            # A morning event for a night will almost always be after
            # solar midnight, and can never be more than a tiny bit
            # before. An extra morning event will be hours before.
            return time_after_midnight <= -_ONE_HOUR
        
        else:
            # evening event
            
            # An evening event for a night will almost always be before
            # solar midnight, and can never be more than a tiny bit
            # after. An extra evening event will be hours after.
            return time_after_midnight >= _ONE_HOUR
 

class SunMoonCache:
    
    
    """
    `SunMoon` cache.
    
    A `SunMoonCache` maintains a cache of `SunMoon` objects. Different
    functions that perform astronomical calculations for the same
    locations can share `SunMoon` objects by getting them from the
    same cache, thus accelerating their calculations.
    
    The `result_times_local` initializer argument determines whether
    the `SunMoon` objects of the cache return local times or UTC times.
    
    The `max_size` initializer argument determines the maximum number
    of `SunMoon` objects the cache will hold. Least recently used
    objects are discarded as needed to keep the cache size from
    exceeding this limit.
    """
    
    
    DEFAULT_MAX_SIZE = 100
    
    
    def __init__(self, result_times_local=False, max_size=DEFAULT_MAX_SIZE):
        
        self._result_times_local = result_times_local
        
        self._sun_moons = LruCache(max_size)
        """
        `SunMoon` cache.
        
        We use the `LruCache` class instead of the `functools.lru_cache`
        decorator to implement caching so we can make the cache size
        configurable via an initializer argument.
        """
    
    
    @property
    def result_times_local(self):
        return self._result_times_local
    
    
    @property
    def max_size(self):
        return self._sun_moons.max_size
    
    
    def get_sun_moon(self, latitude, longitude, time_zone):
        
        """
        Gets a `SunMoon` object for the specified latitude, longitude,
        and time zone.
        
        The `latitude` and `longitude` arguments specify the location
        of the desired `SunMoon` object. They have units of degrees.
        
        The `time_zone` argument specifies the local time zone at the
        `SunMoon` object's location.
        
        Note that a cache stores `SunMoon` objects according to their
        locations, but not their time zones. The time zone of a
        `SunMoon` object is used by the cache only to construct it,
        the first time this method is called for the object's location.
        The time zone is ignored in subsequent calls.
        """
        
        key = (latitude, longitude)
        
        try:
            return self._sun_moons[key]
        
        except KeyError:
            # cache miss
            
            sun_moon = SunMoon(
                latitude, longitude, time_zone, self.result_times_local)
            
            self._sun_moons[key] = sun_moon
            
            return sun_moon
