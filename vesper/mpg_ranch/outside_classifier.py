"""
Module containing class `OutsideClassifier`.

An `OutsideClassifier` assigns the `'Outside'` classification to a clip
if the clip's start time is outside of the interval from one hour after
sunset to one half hour before sunrise, and does nothing otherwise.
"""


import datetime

from vesper.command.annotator import Annotator
from vesper.ephem.astronomical_calculator import AstronomicalCalculatorCache


_START_OFFSET = datetime.timedelta(minutes=60)
_END_OFFSET = datetime.timedelta(minutes=-30)


class OutsideClassifier(Annotator):
    
    
    extension_name = 'MPG Ranch Outside Classifier 1.1'
    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._astronomical_calculators = AstronomicalCalculatorCache()
    
    
    def annotate(self, clip):
        
        clip_start_time = clip.start_time
        station = clip.station
        night = station.get_night(clip_start_time)
        calculator = self._astronomical_calculators.get_calculator(
            station.latitude, station.longitude, station.tz)
        
        # Check if clip start time precedes analysis period.
        sunset_time = calculator.get_night_solar_event_time(night, 'Sunset')
        if sunset_time is not None:
            start_time = sunset_time + _START_OFFSET
            if clip_start_time < start_time:
                self._annotate(clip, 'Outside')
                return True
        
        # Check if clip start time follows analysis period.
        sunrise_time = calculator.get_night_solar_event_time(night, 'Sunrise')
        if sunrise_time is not None:
            end_time = sunrise_time + _END_OFFSET
            if clip_start_time > end_time:
                self._annotate(clip, 'Outside')
                return True
        
        # If we get here, the clip is not outside of the analysis period,
        # so we will not annotate it.
        return False
