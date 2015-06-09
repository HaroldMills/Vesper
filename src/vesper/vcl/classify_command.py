"""Module containing class `ClassifyCommand`."""


from __future__ import print_function

import datetime

from mpg_ranch.outside_clip_classifier \
    import OutsideClipClassifier as MpgRanchOutsideClipClassifier
from vesper.vcl.command import Command, CommandSyntaxError
import vesper.vcl.vcl_utils as vcl_utils


class ClassifyCommand(Command):
    
    """vcl command that classifies clips of an archive."""
    
    
    name = 'classify'
    
    
    @staticmethod
    def get_help_text():
        # TODO: Get help text for individual classifiers from the classifiers.
        return (
            'classify clips '
            '--classifier "MPG Ranch Outside Clip Classifier" '
            '[--station <station name>] [--stations <station names>] '
            '[--detector <detector name>] [--detectors <detector names>] '
            '[--clip-class <clip class name>] '
            '[--clip-classes <clip class names>] '
            '[--date <YYYY-MM-DD>] '
            '[--start-date <YYYY-MM-DD] [--end-date <YYYY-MM-DD>] '
            '[--archive <archive dir>]')

    
    def __init__(self, positional_args, keyword_args):
        
        super(ClassifyCommand, self).__init__()
        
        # TODO: Move this check to superclass.
        if len(positional_args) != 1:
            raise CommandSyntaxError((
                '{:s} command requires exactly one positional '
                'argument.').format(self.name))
            
        klass = _get_classifier_class(positional_args[0])
        self._classifier = klass(positional_args[1:], keyword_args)
        
        
    def execute(self):
        return self._classifier.classify()
        
        
def _get_classifier_class(name):

    try:
        return _CLASSIFIER_CLASSES[name]
    except KeyError:
        raise ValueError(
            'Unrecognized classification object type "{:s}".'.format(name))


class ClipsClassifier(object):
    
    
    def __init__(self, positional_args, keyword_args):
        
        super(ClipsClassifier, self).__init__()
        
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        
        self._station_names, self._detector_names, self._clip_class_names, \
            self._start_date, self._end_date = \
            vcl_utils.get_clip_query(keyword_args)
            
        self._classifier = _get_clip_classifier(positional_args, keyword_args)
                
    
    def classify(self):
        
        archive = vcl_utils.open_archive(self._archive_dir_path)
        
        (station_names, detector_names, clip_class_names, dates) = \
            _get_clip_query_tuples(
                self._station_names, self._detector_names,
                self._clip_class_names, self._start_date, self._end_date,
                archive)
        
#         print('ClipsClassifier.classify', self._archive_dir_path,
#               station_names, detector_names, clip_class_names, dates)
        
        for station_name in station_names:
            for detector_name in detector_names:
                for clip_class_name in clip_class_names:
                    for date in dates:
                        clips = archive.get_clips(
                            station_name, detector_name, date, clip_class_name)
                        for clip in clips:
                            self._classifier.classify(clip)
                        
        archive.close()
        
        return True


_CLIP_CLASSIFIER_CLASSES = {
    'MPG Ranch Outside Clip Classifier': MpgRanchOutsideClipClassifier
}


def _get_clip_classifier(positional_args, keyword_args):

    try:
        (name,) = keyword_args['classifier']
    except KeyError:
        raise CommandSyntaxError(
            'Missing required "classifier" keyword argument.')
    
    try:
        klass = _CLIP_CLASSIFIER_CLASSES[name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized clip classifier "{:s}".'.format(name))

    return klass(positional_args, keyword_args)


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
    
    
_CLASSIFIER_CLASSES = {
    'clips': ClipsClassifier
    # 'clip': ClipClassifier
}
