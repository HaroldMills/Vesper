"""Module containing `ArchiveParser` class."""


import calendar
import datetime

from nfc.util.bunch import Bunch


_MONTH_NAMES = dict((i + 1, s) for (i, s) in enumerate([
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']))


class ArchiveParser(object):
    
    """NFC clip archive parser."""
    
    
    def __init__(self, station_names=None, clip_class_names=None):
        
        self._station_names = _create_set(station_names)
        self._clip_class_names = _create_set(clip_class_names)
        
        self._info = Bunch()
        
        self.num_bad_file_names = 0
        self.num_misplaced_files = 0
        self.num_accepted_files = 0
            
            
    def parse_year_dir_name(self, name):
        
        try:
            year = int(name[:4])
            
        except ValueError:
            self._handle_bad_year_dir_name(name)
            
        if year < 1900:
            self._handle_bad_year_dir_name(name)
            
        elif year > datetime.datetime.now().year:
            raise ValueError('Year {:d} is in the future.')
        
        self._info.year = year
        
        return self._info
    

    def _handle_bad_year_dir_name(self, name):
        self._handle_bad_dir_name('year directory name', name)
        
        
    def _handle_bad_dir_name(self, description, name):
        raise ValueError('Bad {:s} "{:s}".'.format(description, name))


    def parse_station_dir_name(self, name):
    
        if self._station_names is None or name in self._station_names:
            self._info.stationName = name
            return self._info
        
        else:
            raise ValueError('Unrecognized station name "{:s}".'.format(name))
        
        
    def parse_month_dir_name(self, name):
                
        # TODO: Update this method for month directory names that
        # include years.
        
        try:
            month = int(name)
        
        except ValueError:
            self._handle_bad_month_dir_name(name)
            
        if month < 1 or month > 12:
            self._handle_bad_month_dir_name(name)
            
        self._info.month = month
        
        return self._info
            
    
    def _handle_bad_month_dir_name(self, name):
        self._handle_bad_dir_name('month directory name', name)


    def parse_day_dir_name(self, name):
    
        # TODO: Use regular expression here, e.g. to require that name
        # comprise exactly two digits?
        
        try:
            day = int(name)
            
        except:
            self._handle_bad_day_dir_name(name)
        
        info = self._info
        
        self._check_day(day, info.month, info.year, name)
        
        info.day = day
        
        return info


    def _handle_bad_day_dir_name(self, name):
        self._handle_bad_dir_name('day directory name', name)
        

    def _check_day(self, day, month, year, dir_name):
        
        if day < 1:
            self._handle_bad_day_dir_name(dir_name)
        
        else:
            
            (_, month_days) = calendar.monthrange(year, month)
            
            if day > month_days:
                
                month_name = _MONTH_NAMES[month]
                raise ValueError(
                    ('Bad day {:d} is larger than number of days '
                     '({:d}) in {:s}, {:d}.').format(
                        day, month_days, month_name, year))
        
        
    def parse_clip_class_dir_name(self, name, ancestor_dir_names):
        
        if self._clip_class_names is None or name in self._clip_class_names:
            self._info.clip_class_dir_names = ancestor_dir_names + (name,)
            return self._info
        
        else:
            raise ValueError(
                'Unrecognized clip class directory name "{:s}".'.format(name))
        
        
    def parse_clip_class_dir_names(self, names):
        self._info.clip_class_name = '.'.join(names)
        return self._info
    
    
    def parse_clip_file_name(self, file_name, clip_class_name):
        raise NotImplementedError()
    
#         try:
#             info = file_name_utils.parse_clip_file_name(file_name)
#
#         except ValueError:
#             self.num_bad_file_names += 1
#             raise
#
#         try:
#             self._check_clip_info(info)
#
#         except ValueError:
#             self.num_misplaced_files += 1
#             raise
#
#         self.num_accepted_files += 1
#
#         info.clip_class_name = clip_class_name
#
#         return info
        
        
    def _check_clip_info(self, info):

        i = self._info
        time = datetime.datetime(i.year, i.month, i.day, 12, 0, 0)
        
        delta_days = (info.time - time).total_seconds() / (24 * 3600)
        
        if delta_days < 0 or delta_days >= 1:
            raise ValueError(
                'Time of clip is inconsistent with date of containing '
                'day directory.')
        
        
def _create_set(items):
    return None if items is None else frozenset(items)
