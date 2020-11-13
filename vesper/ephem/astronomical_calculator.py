"""Utility functions concerning the sun and moon."""


from pathlib import Path
import datetime

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

All `datetime` objects returned by methods are UTC. If callers want
`datetime` objects in other time zones, they must convert them themselves.

def __init__(self, latitude, longitude, elevation=0)

def get_solar_position(self, dt)

def get_solar_altitude_events(self, start_dt, end_dt)

def get_solar_altitude_period(self, dt)
    
def get_lunar_position(self, dt)
    
def get_lunar_fraction_illuminated(self, dt)


These would be helpful:

    def get_day_solar_altitude_events(self, date)
    def get_day_solar_altitude_event_time(self, event_name, date)
    def get_night_solar_altitude_events(self, date)
    def get_night_solar_altitude_event_time(self, event_name, date)

but would require that a calculator have a time zone.

Or perhaps we should have:

    def get_solar_altitude_events(self, **kwargs)

and require either `start_dt` and `end_dt` or `day` or `night` keyword
arguments? Invocations would look like:

   get_solar_altitude_events(start_dt=start_dt, end_dt=end_dt)
   get_solar_altitude_events(day=day)
   get_solar_altitude_events(night=night)


# Omit these initially. Skyfield does not yet offer moonrise and moonset
# calculations. It is more difficult to calculate lunar altitude events
# than solar altitude events because of the nearness of the moon to the
# earth and the eccentricity of its orbit.
def get_lunar_altitude_events(self, start_dt, end_dt)
def get_lunar_altitude_period(self, dt)
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
    
    
    _eph = None
    _sun = None
    _earth = None
    _moon = None
    _ts = None
    
    
    @classmethod
    def _init_if_needed(cls):
        if cls._eph is None:
            cls._eph = load_file(_EPHEMERIS_FILE_PATH)
            cls._sun = cls._eph['sun']
            cls._earth = cls._eph['earth']
            cls._moon = cls._eph['moon']
            cls._ts = load.timescale()
            
            
    # TODO: What effect does nonzero elevation have on calculated times?
    # If none, maybe we should omit it?
    def __init__(self, latitude, longitude, elevation=0):
        
        AstronomicalCalculator._init_if_needed()
        
        self._lat = latitude
        self._lon = longitude
        self._el = elevation
        
        self._topos = Topos(
            latitude_degrees=self._lat,
            longitude_degrees=self._lon,
            elevation_m=self._el)
        
        self._loc = self._earth + self._topos
        
        self._solar_altitude_period_function = \
            almanac.dark_twilight_day(self._eph, self._topos)
        
        
    @property
    def latitude(self):
        return self._lat
    
    
    @property
    def longitude(self):
        return self._lon
    
    
    @property
    def elevation(self):
        return self._el
    
    
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
                
            return self._ts.from_datetimes(arg)
        
        
    def _get_scalar_skyfield_time(self, dt):
        _check_time_zone_awareness(dt)
        return self._ts.from_datetime(dt)
       

    def get_solar_altitude_events(self, start_dt, end_dt):
        
        # Get start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_dt)
        end_time = self._get_scalar_skyfield_time(end_dt)
        
        # Get solar altitude event times and codes.
        times, codes = almanac.find_discrete(
            start_time, end_time, self._solar_altitude_period_function)
        
        # Get event times as UTC `datetime` objects.
        dts = [t.utc_datetime() for t in times]
        
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
    
    
    def get_solar_altitude_period(self, dt):
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
        return almanac.fraction_illuminated(self._eph, 'moon', t)


def _check_time_zone_awareness(dt):
    tzinfo = dt.tzinfo
    if tzinfo is None or tzinfo.utcoffset(dt) is None:
        raise ValueError('Time does not include a time zone.')
