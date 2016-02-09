"""Module containing `Station` class."""


import pytz

from vesper.util.named import Named
import vesper.archive.archive_shared as archive_shared
import vesper.util.astro_utils as astro_utils


def memoize(function):
    
    results = {}
    
    def aux(self, v):
        try:
            return results[v]
        except KeyError:
            result = function(self, v)
            results[v] = result
            return result
    
    return aux


class Station(Named):
    
    """Recording station."""
    
    
    def __init__(
            self, name, long_name, time_zone_name,
            latitude=None, longitude=None, elevation=None):
        
        super(Station, self).__init__(name)
        self._long_name = long_name
        self._time_zone = pytz.timezone(time_zone_name)
        self._latitude = latitude
        self._longitude = longitude
        self._elevation = elevation
        
        
    @property
    def long_name(self):
        return self._long_name
    
    
    @property
    def time_zone(self):
        return self._time_zone
    
    
    @property
    def latitude(self):
        return self._latitude
    
    
    @property
    def longitude(self):
        return self._longitude
    
    
    @property
    def elevation(self):
        return self._elevation
    
    
    def get_night(self, time):
        
        """
        Gets the station-local night that includes the specified time.
        
        :Parameters:
            time : `datetime`
                the time whose night is to be gotten.
                
                The time may be either naive or aware. If the time
                is naive, it is assumed to be in the station's
                time zone.
                
        :Returns:
            the station-local night that includes the specified time, a `date`.
            
            The station-local night of a time is the starting date of the
            local 24-hour period starting at noon that contains the time.
        """
        
        if time.tzinfo is not None:
            # time is aware
            
            # convert time to station time zone
            time = time.astimezone(self.time_zone)
        
        return archive_shared.get_night(time)
    
    
    @memoize
    def get_sunset_time(self, date):
        lat, lon = self._get_lat_lon()
        return astro_utils.get_sunset_time(lat, lon, date)
        
        
    def _get_lat_lon(self):
        
        lat = self.latitude
        lon = self.longitude
        
        if lat is None or lon is None:
            raise ValueError((
                'Sunset and sunrise times are not available for station '
                '"{:s}" since its location is unknown.').format(self.name))
            
        return (lat, lon)
 
 
    @memoize
    def get_sunrise_time(self, date):
        lat, lon = self._get_lat_lon()
        return astro_utils.get_sunrise_time(lat, lon, date)
