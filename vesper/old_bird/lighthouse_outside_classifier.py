"""
Module containing class `LighthouseOutsideClassifier`.

A `LighthouseOutsideClassifier` assigns the `'Outside'` classification
to a clip if the clip is unclassified and intersects the time interval
from nautical dusk to nautical dawn. It does not modify the clip's
classification otherwise.

"""


import datetime

from vesper.command.annotator import Annotator
import vesper.ephem.ephem_utils as ephem_utils


_ONE_DAY = datetime.timedelta(days=1)


class LighthouseOutsideClassifier(Annotator):
    
    
    extension_name = 'Lighthouse Outside Classifier 1.0'
    
    
    def annotate(self, clip):
        
        classification = self._get_annotation_value(clip)
        
        if classification is not None:
            # clip is classified
            
            return False
        
        else:
            # clip is unclassified
        
            get_event_time = ephem_utils.get_event_time
    
            station = clip.station
            lat = station.latitude
            lon = station.longitude
            
            date = station.get_night(clip.start_time)
            start_time = get_event_time('Nautical Dusk', lat, lon, date)
            
            date += _ONE_DAY
            end_time = get_event_time('Nautical Dawn', lat, lon, date)
    
            if clip.end_time < start_time or clip.start_time > end_time:
                # clip is outside time interval of interest
                
                self._annotate(clip, 'Outside')
                return True
            
            else:
                # clip is inside time interval of interest
                
                return False
