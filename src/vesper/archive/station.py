"""Module containing `Station` class."""


import pytz

from vesper.util.named import Named
import vesper.archive.archive_shared as archive_shared


class Station(Named):
    
    """Nocturnal migration monitoring station."""
    
    
    def __init__(self, name, long_name, time_zone_name):
        super(Station, self).__init__(name)
        self._long_name = long_name
        self._time_zone = pytz.timezone(time_zone_name)
        
        
    @property
    def long_name(self):
        return self._long_name
    
    
    @property
    def time_zone(self):
        return self._time_zone
    
    
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
