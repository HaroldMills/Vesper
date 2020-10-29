"""Utility functions concerning the sun and moon."""


from pathlib import Path
import datetime

from skyfield import almanac
from skyfield.api import Topos, load, load_file
import pytz


'''
Functions we want:

* Given time period, return sequence of (time, event) pairs for
  solar events that occur during that time period. The events are:
  
      Sunrise
      Sunset
      Civil Dawn
      Civil Dusk
      Nautical Dawn
      Nautical Dusk
      Astronomical Dawn
      Astronomical Dusk
  
* Given date, return solar events that occur during the day of that date,
  i.e. from midnight on that date to midnight on the next date.
  
* Given date, return solar events that occur during the night of that date,
  i.e. from noon on that date to noon on the next date.
  
* Given time, return solar period at that time.

* Given time, return sun altitude and azimuth at that time.

* Given time period, return sequence of (time, event) pairs for lunar
  events that occur during that time period. The events are:
  
      Moonrise
      Moonset
      
* Given time, get moon altitude, azimuth, phase, and illumination at that time.
'''

'''
Deline 65.187782, -123.422775
Ithaca 42.431964, -76.501656

Might get test data from timeanddate.com.
'''


# TODO: Include "de421.bsp" file in Vesper package?


_JPL_FILE_PATH = Path(__file__).parent / 'de421.bsp'

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

_ONE_DAY = datetime.timedelta(days=1)


'''
A "day" is a 24 hour period starting 12 hours before local noon.
A "night" is a 24 hour period starting at local noon.

Methods that have `datetime` arguments require that those arguments be
time-zone-aware.

All `datetime` objects returned by methods are UTC. If callers want
`datetime` objects in other time zones, they must convert them themselves.


def __init__(self, latitude, longitude, elevation=0)

def get_solar_position(self, dt)

def get_solar_events(self, start_dt, end_dt)

def get_day_solar_events(self, date)
    
def get_night_solar_events(self, date)
    
def get_solar_period(self, dt)
    
def get_lunar_position(self, dt)
    
def get_lunar_events(self, start_dt, end_dt)
    
def get_day_lunar_events(self, date)
    
def get_night_lunar_events(self, date)
    
def get_lunar_phase(self, dt)
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
            # print(f'JPL file path is "{_JPL_FILE_PATH}".')
            cls._eph = load_file(_JPL_FILE_PATH)
            cls._sun = cls._eph['sun']
            cls._earth = cls._eph['earth']
            cls._moon = cls._eph['moon']
            cls._ts = load.timescale()
            
            
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
        
        self._local_time_offset = _get_local_time_offset(longitude)
        
        
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
       

    '''
    K A N C D C N A K
    K A N C N A K
    K A N A K
    K A K
    K
    
    D C N A K A N C D
    D C N A N C D
    D C N C D
    D C D
    D
    
    D: {C}
    C: {N, D}
    N: {A, C}
    A: {K, N}
    K: {A}
    
    K
        -18
    A
        -12
    N
        -6
    C
        -.8333
    D
    '''
    
    
    def get_solar_events(self, start_dt, end_dt):
        
        # Get start and end times as Skyfield `Time` objects.
        start_time = self._get_scalar_skyfield_time(start_dt)
        end_time = self._get_scalar_skyfield_time(end_dt)
        
        # Get solar event times and codes.
        function = almanac.dark_twilight_day(self._eph, self._topos)
        times, codes = almanac.find_discrete(start_time, end_time, function)
        
        # Get event times as UTC `datetime` objects.
        dts = [t.utc_datetime() for t in times]
        
        # Get solar event names.
        names = self._get_solar_event_names(dts, codes)
        
        # Combine event times and names into pairs.
        events = list(zip(dts, names))
        
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
                self._get_solar_event_name(codes[i], codes[i + 1])
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
            
            
    def _get_solar_event_name(self, code_0, code_1):
        return _SOLAR_EVENT_NAMES[(code_0, code_1)]
    
    
    def get_day_solar_events(self, date):
        return self._get_solar_events_aux(date, 0)
    
    
    def _get_solar_events_aux(self, date, start_hour):
        
        # Get event period start at prime meridian.
        start_dt = datetime.datetime(
            date.year, date.month, date.day, start_hour, tzinfo=pytz.utc)
        
        # Adjust for longitude of this calculator.
        start_dt += self._local_time_offset
        
        # Get event period end time.
        end_dt = start_dt + _ONE_DAY
        
        # Get events.
        return self.get_solar_events(start_dt, end_dt)
    
    
    def get_night_solar_events(self, date):
        return self._get_solar_events_aux(date, 12)
    
    
    def get_solar_period(self, dt):
        pass
    
    
    def get_lunar_position(self, dt):
        return self._get_position(self._moon, dt)
    
    
    def get_lunar_events(self, start_dt, end_dt):
        pass
    
    
    def get_day_lunar_events(self, date):
        pass
    
    
    def get_night_lunar_events(self, date):
        pass
    
    
    def get_lunar_phase(self, dt):
        pass


def _get_local_time_offset(longitude):
    
    # Normalize longitude to [-180, 180).
    while longitude < -180:
        longitude += 360
    while longitude >= 180:
        longitude -= 360
        
    # Get longitude in units of hours east.
    hours = 24 * longitude / 360
    
    # Get offset as `timedelta`.
    offset = datetime.timedelta(hours=-hours)
    
    return offset
        
        
def _check_time_zone_awareness(dt):
    tzinfo = dt.tzinfo
    return tzinfo is not None and tzinfo.utcoffset(dt) is not None
