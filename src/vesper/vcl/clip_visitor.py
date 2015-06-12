"""Module containing class `ClipVisitor`."""


import datetime

from vesper.vcl.visitor import Visitor
import vesper.vcl.vcl_utils as vcl_utils


class ClipVisitor(Visitor):
    
    """
    Abstract archive clip visitor superclass.
    
    A *clip visitor* visits each clip of a set of clips from an archive,
    performing some operation (for example, classification or export) on
    the clip.
    """
    
    
    def __init__(self, positional_args, keyword_args):
        
        super(ClipVisitor, self).__init__(positional_args, keyword_args)
        
        self._station_names, self._detector_names, self._clip_class_names, \
            self._start_date, self._end_date = \
            vcl_utils.get_clip_query(keyword_args)
                
    
    def objects(self):
        
        # TODO: Provide more control of the order in which clips are visited,
        # perhaps with a "--clip-order" keyword argument.
        
        (station_names, detector_names, clip_class_names, dates) = \
            _get_clip_query_tuples(
                self._station_names, self._detector_names,
                self._clip_class_names, self._start_date, self._end_date,
                self._archive)
            
        for station_name in station_names:
            for detector_name in detector_names:
                for clip_class_name in clip_class_names:
                    for date in dates:
                        
                        clips = self._archive.get_clips(
                            station_name, detector_name, date,
                            clip_class_name)
                        
                        for clip in clips:
                            yield clip
                            
                            
    visit_clips = Visitor.visit_objects


def _get_clip_query_tuples(
        station_names, detector_names, clip_classes, start_date, end_date,
        archive):
    
    station_names = _get(station_names, (None,))
    detector_names = _get(detector_names, (None,))
    clip_classes = _get(clip_classes, (None,))
    
    start_date = _get(start_date, archive.start_night)
    end_date = _get(end_date, archive.end_night)
    end_date += datetime.timedelta(days=1)
    dates = _get_dates(start_date, end_date)
    
    return station_names, detector_names, clip_classes, dates
    
    
def _get(arg, none_result):
    return none_result if arg is None else arg


def _get_dates(start_date, end_date):
    num_days = int((end_date - start_date).days)
    days = lambda i: datetime.timedelta(days=i)
    return tuple(start_date + days(i) for i in xrange(num_days))
