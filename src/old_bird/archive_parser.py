"""Module containing `OldBirdArchiveParser` class."""


import datetime
from nfc.archive.archive import Archive
from nfc.archive.archive_parser import ArchiveParser
from old_bird.archive_constants import STATIONS, CLIP_CLASSES
import old_bird.file_name_utils as file_name_utils


_MONTH_PREFIXES = [
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

_MONTH_NUMS = dict((s, i + 1) for (i, s) in enumerate(_MONTH_PREFIXES))


_CLIP_CLASS_DIR_NAMES = \
    Archive.get_clip_class_name_components(CLIP_CLASSES) + \
    ['Classified', 'Unclassified']

_CLIP_CLASS_DIR_NAME_CORRECTIONS = {
    'Calls': 'Call',
    'Oven': 'OVEN',
    'PALM': 'PAWA',
    'Palm': 'PAWA',
    'PAWA': 'NOPA',
    'ShDbUp': 'DbUp',
    'Tones': 'Tone',
    'Unkn': 'Unknown'
}

_CLIP_CLASS_NAMES = {
    'Call': 'Call',
    'Noise': 'Noise',
    'Tone': 'Tone',
    'Classified': None,
    'Unclassified': None,
    'Songtype': 'Call.WTSP.Songtype'
}


class OldBirdArchiveParser(ArchiveParser):
    
    """Clip archive parser for Summer and Fall 2012 Old Bird data."""
    
    
    def __init__(self):
        
        station_names = [s.name for s in STATIONS]
        
        super(OldBirdArchiveParser, self).__init__(station_names)
        
        self.num_absolute_file_names = 0
        self.num_relative_file_names = 0
        self.num_unresolved_relative_file_names = 0
        
        
    def parse_month_dir_name(self, name):
        
#        self._handle_bad_month_dir_name(name)

        info = self._info
        
        prefix = name[:3].lower()
        
        try:
            info.month = _MONTH_NUMS[prefix]
        
        except KeyError:
            self.handle_bad_month_dir_name(name)
            
        return info
    
    
    def parse_day_dir_name(self, name):
    
        info = self._info
        
        try:
            
            (start_day, end_day) = name.split('-')
            
            start_day = int(start_day)
            
            i = 1 if not end_day[1].isdigit() else 2
            month_prefix = end_day[i:i + 3].lower()
            month = _MONTH_NUMS[month_prefix]
            end_day = int(end_day[:i])
            
        except:
            self._handle_bad_day_dir_name(name)

        year = info.year

        if end_day == 1:
            month -= 1
            if month == 0:
                month = 12
                year -= 1
                
        self._check_day(start_day, month, year, name)
        
        info.year = year
        info.month = month
        info.day = start_day
        
        return info


    def parse_clip_class_dir_name(self, name, ancestor_dir_names):
        
        name = _capitalize(name)
        name = _CLIP_CLASS_DIR_NAME_CORRECTIONS.get(name, name)
        
        if name in _CLIP_CLASS_DIR_NAMES:
            self._info.clip_class_dir_names = ancestor_dir_names + (name,)
            return self._info
        
        else:
            raise ValueError(
                'Unrecognized clip class directory name "{:s}".'.format(name))
    
    
    def parse_clip_class_dir_names(self, names):
        
        if len(names) == 0:
            self._info.clip_class_name = None
            
        else:
            name = names[-1]
            self._info.clip_class_name = \
                _CLIP_CLASS_NAMES.get(name, 'Call.' + name)
            
        return self._info
    
    
    def parse_clip_file_name(self, file_name, clip_class_name):
        
        utils = file_name_utils
        
        try:
            info = utils.parse_clip_file_name(file_name)
            
        except ValueError:
            
            try:
                info = utils.parse_relative_clip_file_name(file_name)
                    
            except ValueError:
                self.num_bad_file_names += 1
                raise
            
            self.num_relative_file_names += 1
                
            try:
                self._adjust_clip_info_start_time(info, file_name)
                
            except ValueError:
                self.num_unresolved_relative_file_names += 1
                raise
            
        else:
            self.num_absolute_file_names += 1
            
        try:
            self._check_clip_info(info)
            
        except ValueError:
            self.num_misplaced_files += 1
            raise
        
        self.num_accepted_files += 1
        
        info.station_name = self._info.station_name
        info.clip_class_name = clip_class_name
        
        return info
    
    
    def _adjust_clip_info_start_time(self, info, file_name):
        
        start_time = self._get_monitoring_start_time()
        
        if start_time is None:
            
            raise ValueError(
                ('Could not get monitoring start time for relative clip file '
                 'name "{:s}".').format(file_name))
            
        else:
            # got monitoring start time
            
            time = info.time
            
            delta = datetime.timedelta(
                hours=time.hour,
                minutes=time.minute,
                seconds=time.second,
                microseconds=time.microseconds)
            
            info.time = start_time + delta
            
            
    # TODO: Implement this.
    def _get_monitoring_start_time(self):
        
        """
        Gets the monitoring start time for the station, year, month,
        and date of the current clip.
        """
        
        return None
    
    
    def _check_clip_info(self, info):
        
        # The `_check_clip_info` method of the `ArchiveParser` class
        # compares the time of a clip to the year, month, and day of
        # the day directory that contains it and raises a `ValueError`
        # if the two are inconsistent. It turned out, however, that in
        # Bill's data there were many files that were in the wrong day
        # directories because the directories were created and files were
        # moved into them manually. It was particularly common for files
        # to appear in the next day's directory, since sometimes files
        # were processed one day after they were recorded and were
        # mistakenly moved into that day's directory. Bill and I decided
        # to just ignore the day directory information and process the
        # files according to the times indicated in their names.
        
        pass


def _capitalize(s):
    return s[0].capitalize() + s[1:] if s else s
