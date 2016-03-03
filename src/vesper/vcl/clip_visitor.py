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
    
    
    arg_descriptors = \
        Visitor.arg_descriptors + vcl_utils.CLIP_QUERY_ARG_DESCRIPTORS


    def __init__(self, positional_args, keyword_args):
        
        super(ClipVisitor, self).__init__(positional_args, keyword_args)
        
        self._station_names, self._detector_names, self._clip_class_names, \
            self._start_night, self._end_night = \
            vcl_utils.get_clip_query(keyword_args)
                
    
    def objects(self):
        
        # TODO: Provide more control of the order in which clips are visited,
        # perhaps with a "--clip-order" keyword argument.
        
        (station_names, detector_names, clip_class_names, nights) = \
            _get_clip_query_tuples(
                self._station_names, self._detector_names,
                self._clip_class_names, self._start_night, self._end_night,
                self._archive)
            
        for station_name in station_names:
            for detector_name in detector_names:
                for clip_class_name in clip_class_names:
                    for night in nights:
                        
                        clips = self._archive.get_clips(
                            station_name, detector_name, night,
                            clip_class_name)
                        
                        # Clips come from the archive sorted by start time.
                        # Resort by the combination of clip class name and
                        # start time.
                        clips.sort(
                            key=lambda c: (c.clip_class_name, c.start_time))
                        
                        for clip in clips:
                            yield clip
                            
                            
    visit_clips = Visitor.visit_objects


def _get_clip_query_tuples(
        station_names, detector_names, clip_class_names, start_night,
        end_night, archive):
    
    # When station names and/or detector names are not specified, we
    # return a list of all of them. When clip class names are not
    # specified, however, we return a tuple containing just `None`.
    # This asymmetry is because in order to keep archive clip query
    # results within reasonable size limits we want to query for
    # clips one combination of station, detector, and night at a
    # time. However, we do not mind querying for all clip classes
    # at once.

    if station_names is None:
        station_names = tuple(s.name for s in archive.stations)
    
    if detector_names is None:
        detector_names = tuple(d.name for d in archive.detectors)
        
    clip_class_names = _get(clip_class_names, (None,))
    
    start_night = _get(start_night, archive.start_night)
    end_night = _get(end_night, archive.end_night)
    end_night += datetime.timedelta(days=1)
    nights = _get_dates(start_night, end_night)
    
    return station_names, detector_names, clip_class_names, nights
    
    
def _get(arg, default):
    return default if arg is None else arg


def _get_dates(start_date, end_date):
    num_dates = int((end_date - start_date).days)
    days = lambda i: datetime.timedelta(days=i)
    return tuple(start_date + days(i) for i in xrange(num_dates))
