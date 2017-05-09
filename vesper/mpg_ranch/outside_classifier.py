"""
Module containing class `OutsideClassifier`.

An `OutsideClassifier` assigns the `'Outside'` classification to a clip
if the clip's start time is outside of the interval from one hour after
sunset to one half hour before sunrise, and does nothing otherwise.
"""

import datetime
import logging

from vesper.command.annotator import Annotator
import vesper.ephem.ephem_utils as ephem_utils


_logger = logging.getLogger()


_START_OFFSET = datetime.timedelta(minutes=60)
_END_OFFSET = datetime.timedelta(minutes=-30)
_ONE_DAY = datetime.timedelta(days=1)


class OutsideClassifier(Annotator):
    
    
    extension_name = 'MPG Ranch Outside Classifier 1.0'
    
    
    def annotate(self, clip):
        
        annotated = False
        
        station = clip.station
        lat = station.latitude
        lon = station.longitude
        
        # TODO: Perhaps (at this point at least) we should require that
        # each station have a latitude, a longitude, and an elevation.
        
        if lat is None or lon is None:
            
            _logger.warning(
                'Station "{}" has no latitude and/or longitude, so the '
                'outside classifier cannot classify its clips.'.format(
                    station.name))
            
        else:
        
            get_event_time = ephem_utils.get_event_time
        
            night = station.get_night(clip.start_time)
            sunset_time = get_event_time('Sunset', lat, lon, night)
            start_time = sunset_time + _START_OFFSET
            
            sunrise_date = night + _ONE_DAY
            sunrise_time = get_event_time('Sunrise', lat, lon, sunrise_date)
            end_time = sunrise_time + _END_OFFSET
            
            if clip.start_time < start_time or clip.start_time > end_time:
                self._annotate(clip, 'Outside')
                annotated = True
                
        return annotated
