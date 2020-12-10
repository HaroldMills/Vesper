"""Module containing class `AstronomicalCalculator`."""


from pathlib import Path
import datetime
import pytz

from skyfield import almanac
from skyfield.api import Topos, load, load_file


_EPHEMERIS_FILE_PATH = Path(__file__).parent / 'data' / 'de421.bsp'
"""
Jet Propulsion Laboratory Development Ephemeris (JPL DE) Spice Planet
Kernel (SPK) file path. See
en.wikipedia.org/wiki/Jet_Propulsion_Laboratory_Development_Ephemeris
for a discussion of the JPL DE.

See https://pypi.org/project/jplephem/ for instructions on excerpting
SPK files. This might be a good idea to reduce the SPK file size.
"""

_SOLAR_ALTITUDE_EVENT_NAMES = {
    (0, 1): 'Astronomical Dawn',
    (1, 2): 'Nautical Dawn',
    (2, 3): 'Civil Dawn',
    (3, 4): 'Sunrise',
    (4, 3): 'Sunset',
    (3, 2): 'Civil Dusk',
    (2, 1): 'Nautical Dusk',
    (1, 0): 'Astronomical Dusk'
}

_SOLAR_ALTITUDE_PERIOD_NAMES = {
    0: 'Night',
    1: 'Astronomical Twilight',
    2: 'Nautical Twilight',
    3: 'Civil Twilight',
    4: 'Day'
}

_ONE_DAY = datetime.timedelta(days=1)


'''
Methods that have `datetime` arguments require that those arguments be
time-zone-aware.

Methods that have `day` or `night` in their names require that the
`local_time_zone` attribute be set. They will raise an exception if
it is the default `None`.

All `datetime` objects returned by methods are in the `result_time_zone`
time zone.


Methods:

def __init__(
    self, latitude, longitude, elevation=0, local_time_zone=None,
    result_time_zone='UTC')

def get_solar_position(self, dt)

def get_solar_altitude_events(self, start_dt, end_dt)

def get_day_solar_altitude_events(self, date)

def get_day_solar_altitude_event_time(self, event_name, date)

def get_night_solar_altitude_events(self, date)

def get_night_solar_altitude_event_time(self, event_name, date)

def get_solar_altitude_period_name(self, dt)
    
def get_lunar_position(self, dt)
    
def get_lunar_fraction_illuminated(self, dt)


Omit the following methods initially. Skyfield does not yet offer
moonrise and moonset calculations. It is more difficult to calculate
lunar altitude events than solar altitude events because of the
nearness of the moon to the earth and the eccentricity of its orbit.
These make the angle subtended by the moon more variable than the
angle subtended by the sun.

def get_lunar_altitude_events(self, start_dt, end_dt)
def get_lunar_altitude_period_name(self, dt)
'''


'''
Solar altitude period definitions, with numbers in degrees:

Night: altitude < -18
Astronomical Twilight: -18 <= altitude < -12
Nautical Twilight: -12 <= altitude < -6
Civil Twilight: -6 <= altitude < -.833333
Day: altitude >= -8.33333
'''
    
    
class AstronomicalCalculator:
    
    
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
            
            
    # TODO: Look into effect of nonzero elevations on calculated times.
    def __init__(
            self, latitude, longitude, elevation=0,
            local_time_zone=None, result_time_zone='UTC'):
        
        AstronomicalCalculator._init_if_needed()
        
        self._lat = latitude
        self._lon = longitude
        self._el = elevation
        
        self._local_time_zone = local_time_zone
        if isinstance(self.local_time_zone, str):
            self._local_time_zone = pytz.timezone(self._local_time_zone)
            
        self._result_time_zone = result_time_zone
        if self._result_time_zone is None:
            self._result_time_zone = pytz.utc
        elif isinstance(self._result_time_zone, str):
            self._result_time_zone = pytz.timezone(self._result_time_zone)
 
        self._topos = Topos(
            latitude_degrees=self._lat,
            longitude_degrees=self._lon,
            elevation_m=self._el)
        
        self._loc = self._earth + self._topos
        
        self._solar_altitude_period_function = \
            almanac.dark_twilight_day(self._ephemeris, self._topos)
        
        
    @property
    def latitude(self):
        return self._lat
    
    
    @property
    def longitude(self):
        return self._lon
    
    
    @property
    def elevation(self):
        return self._el
    
    
    @property
    def local_time_zone(self):
        return self._local_time_zone
    
    
    @property
    def result_time_zone(self):
        return self._result_time_zone
    
    
    def get_solar_position(self, dt):
        return self._get_position(self._sun, dt)
    
    
    def _get_position(self, body, dt):
        t = self._get_skyfield_time(dt)
        return self._loc.at(t).observe(body).apparent().altaz()
    
    
    def _get_skyfield_time(self, arg):
        
        if isinstance(arg, datetime.datetime):
            return self._get_scalar_skyfield_time(arg)
            
        else:
            # assume `arg` is sequence of `datetime` objects
            
            for dt in arg:
                _check_time_zone_awareness(dt)
                
            return self._timescale.from_datetimes(arg)
        
        
    def _get_scalar_skyfield_time(self, dt):
        _check_time_zone_awareness(dt)
        return self._timescale.from_datetime(dt)
       

    def get_solar_altitude_events(self, start_dt, end_dt):
        
        # Get start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_dt)
        end_time = self._get_scalar_skyfield_time(end_dt)
        
        # Get solar altitude event times and codes.
        times, codes = almanac.find_discrete(
            start_time, end_time, self._solar_altitude_period_function)
        
        # Get event times as `datetime` objects in the appropriate time zone.
        time_zone = self._result_time_zone
        dts = [t.utc_datetime().astimezone(time_zone) for t in times]
        
        # Get event names.
        names = self._get_solar_altitude_event_names(dts, codes)
        
        # Combine event times and names into pairs.
        events = list(zip(dts, names))
        
        return events
    
    
    def _get_solar_altitude_event_names(self, times, codes):
        
        event_count = len(codes)
        
        if event_count == 0:
            return []
        
        else:
            # have at least one event
            
            first_event_name = \
                self._get_first_solar_altitude_event_name(times[0], codes[0])
                
            other_event_names = [
                self._get_solar_altitude_event_name(codes[i], codes[i + 1])
                for i in range(event_count - 1)]
            
            return [first_event_name] + other_event_names
            
            
    def _get_first_solar_altitude_event_name(self, time, code):
        
        if code == 0:
            # event is at start of night
            
            return 'Astronomical Dusk'
        
        elif code == 4:
            # event is at start of day
            
            return 'Sunrise'
        
        else:
            # code could indicate either of two events
            
            altitude, _, _ = self.get_solar_position(time)
            altitude = altitude.degrees
            
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
            
            
    def _get_solar_altitude_event_name(self, code_0, code_1):
        return _SOLAR_ALTITUDE_EVENT_NAMES[(code_0, code_1)]
    
    
    def get_day_solar_altitude_events(self, date):
        return self._get_date_solar_altitude_events(date, True)
    
    
    def _get_date_solar_altitude_events(self, date, day):
        
        self._check_local_time_zone()
        
        if day:
            start_dt, end_dt = self._get_day_time_bounds(date)
        else:
            start_dt, end_dt = self._get_night_time_bounds(date)
            
        return self.get_solar_altitude_events(start_dt, end_dt)
    
    
    def _check_local_time_zone(self):
        if self._local_time_zone is None:
            raise ValueError(
                'Local time zone not set. Cannot compute day or night '
                'solar altitude events without a local time zone.')
            
            
    def _get_day_time_bounds(self, date):
        naive_start_dt = datetime.datetime(date.year, date.month, date.day)
        start_dt = self._local_time_zone.localize(naive_start_dt)
        end_dt = start_dt + _ONE_DAY
        return start_dt, end_dt
        
        
    def get_day_solar_altitude_event_time(self, date, event_name):
        return self._get_date_solar_altitude_event_time(date, event_name, True)
        
        
    def _get_date_solar_altitude_event_time(self, date, event_name, day):
        
        if day:
            events = self.get_day_solar_altitude_events(date)
        else:
            events = self.get_night_solar_altitude_events(date)
        
        # We look through the events in temporal order for one with the
        # specified name to guarantee that if there is more than one
        # event with that name (a rare occurrence, but not impossible),
        # we return the time of the first event.
        for time, name in events:
            if name == event_name:
                return time
 
        # If we get here, there was no event with the specified name.
        return None
    
    
    def get_night_solar_altitude_events(self, date):
        return self._get_date_solar_altitude_events(date, False)
    
    
    def _get_night_time_bounds(self, date):
        naive_start_dt = datetime.datetime(date.year, date.month, date.day, 12)
        start_dt = self._local_time_zone.localize(naive_start_dt)
        end_dt = start_dt + _ONE_DAY
        return start_dt, end_dt
        
        
    def get_night_solar_altitude_event_time(self, date, event_name):
        return self._get_date_solar_altitude_event_time(
            date, event_name, False)
            
    
    def get_solar_altitude_period_name(self, dt):
        arg = self._get_skyfield_time(dt)
        period_codes = self._solar_altitude_period_function(arg)
        if len(period_codes.shape) == 0:
            period_names = _SOLAR_ALTITUDE_PERIOD_NAMES[float(period_codes)]
        else:
            period_names = [
                _SOLAR_ALTITUDE_PERIOD_NAMES(c) for c in period_codes]
        return period_names
    
    
    def get_lunar_position(self, dt):
        return self._get_position(self._moon, dt)
    
    
    def get_lunar_fraction_illuminated(self, dt):
        t = self._get_skyfield_time(dt)
        return almanac.fraction_illuminated(self._ephemeris, 'moon', t)


def _check_time_zone_awareness(dt):
    tzinfo = dt.tzinfo
    if tzinfo is None or tzinfo.utcoffset(dt) is None:
        raise ValueError('Time does not include a time zone.')
