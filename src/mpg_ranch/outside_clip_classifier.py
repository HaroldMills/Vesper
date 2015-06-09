"""
Module containing class `OutsideClipClassifier`.

An `OutsideClipClassifier` assigns the `'Outside'` clip class to a clip
whose start time is outside of the interval from one hour after sunset
to one half hour before sunrise, and does nothing otherwise.
"""


from __future__ import print_function

import datetime


_START_OFFSET = 60
_END_OFFSET = -30


class OutsideClipClassifier(object):
    
    
    def __init__(self, positional_args, keyword_args):
        super(OutsideClipClassifier, self).__init__()
        
        
    def classify(self, clip):
        
        # In this method we assume that every station we encounter
        # will have a location, so that we do not need to handle
        # the `ValueError` exceptions that are raised by the
        # `get_sunset_time` and `get_sunrise_time` methods of the
        # `Station` class for such stations.
        
        timedelta = datetime.timedelta
        
        station = clip.station
        
        sunset_time = station.get_sunset_time(clip.night)
        start_time = sunset_time + timedelta(minutes=_START_OFFSET)
        
        sunrise_date = clip.night + timedelta(days=1)
        sunrise_time = station.get_sunrise_time(sunrise_date)
        end_time = sunrise_time + timedelta(minutes=_END_OFFSET)
        
        time = clip.start_time
        outside = time < start_time or time > end_time
        
        if outside:
            
            clip.clip_class_name = 'Outside'
            
#             print(clip.start_time,
#                   'sunset', sunset_time, 'start', start_time,
#                   'sunrise', sunrise_time, 'end', end_time,
#                   'outside', outside)
