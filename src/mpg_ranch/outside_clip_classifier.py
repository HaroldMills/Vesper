"""
Module containing class `OutsideClipClassifier`.

An `OutsideClipClassifier` assigns the `'Outside'` clip class to a clip
whose start time is outside of the interval from one hour after sunset
to one half hour before sunrise, and does nothing otherwise.
"""


from __future__ import print_function

import datetime

from vesper.vcl.clip_visitor import ClipVisitor
import vesper.util.text_utils as text_utils
import vesper.vcl.vcl_utils as vcl_utils


_HELP = '''
<keyword arguments>

Classifies clips outside the regular MPG Ranch monitoring period as "Outside".

The regular MPG Ranch monitoring period extends from one hour after sunset
to one half hour before sunrise. This command assigns the "Outside" clip
class to clips whose start times are outside of that interval. It does
not alter the clip classes of clips whose start times are within that
interval.

For each clip, the appropriate sunrise and sunset times are calculated
according to the latitude and longitude of the station at which the clip
was recorded, and the night on which it was recorded.

See the keyword arguments documentation for how to specify the archive
in which clips are to be classified, and the subset of clips of that
archive to be classified.
'''.strip()


_ARG_DESCRIPTORS = \
    vcl_utils.ARCHIVE_ARG_DESCRIPTORS + \
    vcl_utils.CLIP_QUERY_ARG_DESCRIPTORS
    
    
# TODO: Make these command line arguments? But maybe that increases the
# probability that one will be set incorrectly...
_START_OFFSET = 60
_END_OFFSET = -30


class OutsideClipClassifier(object):
    
    
    name = 'MPG Ranch Outside Clip Classifier'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(OutsideClipClassifier.name)
        arg_descriptors = _ClipVisitor.arg_descriptors
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(OutsideClipClassifier, self).__init__()
        self._clip_visitor = _ClipVisitor(positional_args, keyword_args)
        
        
    def classify(self):
        return self._clip_visitor.visit_clips()
        
        
class _ClipVisitor(ClipVisitor):
    
    
    def visit(self, clip):
        
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
