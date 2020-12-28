import pytz


class Location:
    
    
    def __init__(self, latitude, longitude, time_zone):
        
        self._latitude = latitude
        self._longitude = longitude
        
        if isinstance(time_zone, str):
            self._time_zone = pytz.timezone(time_zone)
        else:
            self._time_zone = time_zone
    
    
    @property
    def latitude(self):
        return self._latitude
    
    
    @property
    def longitude(self):
        return self._longitude
    
    
    @property
    def time_zone(self):
        return self._time_zone
