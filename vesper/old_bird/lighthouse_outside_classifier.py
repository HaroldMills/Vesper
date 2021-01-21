"""
Module containing class `LighthouseOutsideClassifier`.

A `LighthouseOutsideClassifier` assigns the `'Outside'` classification
to a clip if the clip is unclassified and intersects the time interval
from nautical dusk to nautical dawn. It does not modify the clip's
classification otherwise.
"""


from vesper.command.annotator import Annotator
from vesper.ephem.astronomical_calculator import AstronomicalCalculatorCache


class LighthouseOutsideClassifier(Annotator):
    
    
    extension_name = 'Lighthouse Outside Classifier 1.1'
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._astronomical_calculators = AstronomicalCalculatorCache()
    
    
    def annotate(self, clip):
        
        classification = self._get_annotation_value(clip)
        
        if classification is None:
            # clip is not classified
            
            clip_start_time = clip.start_time
            station = clip.station
            calculator = self._astronomical_calculators.get_calculator(
                station.latitude, station.longitude, station.tz)
            get_event_time = calculator.get_night_solar_event_time
            night = station.get_night(clip_start_time)
            
            # Check if clip start time precedes analysis period.
            start_time = get_event_time(night, 'Nautical Dusk')
            if start_time is not None and clip_start_time < start_time:
                self._annotate(clip, 'Outside')
                return True
            
            # Check if clip start time follows analysis period.
            end_time = get_event_time(night, 'Nautical Dawn')
            if end_time is not None and clip_start_time > end_time:
                self._annotate(clip, 'Outside')
                return True
            
        # If we get here, the clip is already classified or within the
        # analysis period (possibly both), so we will not annotate it.
        return False
