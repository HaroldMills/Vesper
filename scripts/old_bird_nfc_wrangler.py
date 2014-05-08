"""Creates a clip archive from Old Bird clip directories."""


from __future__ import print_function

import argparse
import calendar
import datetime
import logging
import os
import sys

from nfc.archive.archive import Archive
from nfc.util.audio_file_utils import WAVE_FILE_NAME_EXTENSION
from nfc.util.directory_visitor import DirectoryVisitor
import old_bird.file_name_utils as file_name_utils


# from nfc.archive.archive_walker import ArchiveWalker
# from nfc.archive.copying_archive_visitor import CopyingArchiveVisitor
# from old_bird.archive_constants import (
#     CLIP_CLASSES, DETECTORS, STATIONS)
# from old_bird.archive_parser import OldBirdArchiveParser
# 
# 
# _NFC_DIR_PATH = '/Users/Harold/Desktop/NFC/Clips/Old Bird'
# _FROM_PATH = os.path.join(_NFC_DIR_PATH, '2012 Summer and Fall Uncleaned')
# _TO_PATH = os.path.join(_NFC_DIR_PATH, '2012 Summer and Fall')
# 
# 
# def _main():
#     
#     parser = OldBirdArchiveParser()
#     walker = ArchiveWalker(parser)
#     
#     _create_dir(_TO_PATH)
#     
#     visitor = CopyingArchiveVisitor(
#         _TO_PATH, STATIONS, DETECTORS, CLIP_CLASSES)
#     walker.add_visitor(visitor)
#     
#     walker.walk_archive(_FROM_PATH)
#     
#     visitor.visiting_complete()
#     
#     print('Found {:d} absolute clip file names.'.format(
#               parser.num_absolute_file_names))
#     print(('Found {:d} relative clip file names, of which {:d} could ',
#            'not be resolved.').format(
#               parser.num_relative_file_names,
#               parser.num_unresolved_relative_file_names))
#     print('Found {:d} bad clip file names.'.format(parser.num_bad_file_names))
#     print('Ignored {:d} clip files.'.format(walker.num_ignored_files))
#     print('Accepted {:d} clip files.'.format(parser.num_accepted_files))
#     
#     print('{:d} clip files were duplicates.'.format(
#               visitor.num_duplicate_files))
#     print('{:d} sound files were bad.'.format(visitor.num_bad_files))
#     print('{:d} clips could not be added to the archive.'.format(
#               visitor.num_add_errors))
#     
# 
# def _create_dir(path):
#     if not os.path.exists(path):
#         os.makedirs(_TO_PATH)
  
        
_STATION_NAME_CORRECTIONS = {
    'AJO': 'Ajo'
}

_STATION_NAMES = frozenset([
    'Ajo', 'Alfred', 'ColumbiaLC', 'Danby', 'Derby', 'HSHS', 'Jamestown',
    'LTU', 'Minatitlan', 'NMHS', 'Oneonta', 'Ottawa', 'Skinner', 'WFU'])

#_STATION_NAMES = frozenset(['Alfred'])

_DETECTOR_NAMES = frozenset(['Tseep'])

_CLIP_CLASS_DIR_NAME_CORRECTIONS = {                 
    'calls': 'call',
    'tones': 'tone',
    'palm': 'pawa',
    'shdbup': 'dbup',
    'unkn': 'unknown'
}
'''
Mapping from lower case clip class directory names to their lower case
corrections.
'''

_CALL_CLIP_CLASS_NAMES = frozenset([
                          
    'AMRE', 'ATSP', 'BAWW', 'BRSP', 'BTBW', 'CAWA', 'CCSP', 'CHSP',
    'CMWA', 'COYE', 'CSWA', 'FOSP', 'GHSP', 'HESP', 'HOWA', 'INBU',
    'LALO', 'LCSP', 'MOWA', 'NOPA', 'NWTH', 'OVEN', 'PAWA', 'PROW',
    'SNBU', 'SVSP', 'VESP', 'WCSP', 'WIWA', 'WTSP', 'YRWA',
    
    'WTSP.Songtype',
    
    'DbUp', 'Other', 'SNBULALO', 'SwLi', 'Unknown', 'Weak', 'Zeep'

])

_CLIP_CLASS_NAMES = frozenset(
    ['Call', 'Noise', 'Tone'] + ['Call.' + n for n in _CALL_CLIP_CLASS_NAMES])
'''list of clip class names'''
    
_CLIP_CLASS_NAMES = dict(
    [(n.split('.')[-1].lower(), n) for n in _CLIP_CLASS_NAMES] +
    [('classified', 'Call'), ('unclassified', None)])
'''mapping from capitalized clip class directory names to clip class names'''

_MONTH_PREFIXES = [
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

_MONTH_NUMS = dict((s, i + 1) for (i, s) in enumerate(_MONTH_PREFIXES))

_MONTH_PREFIXES = frozenset(_MONTH_PREFIXES)

_MONTH_NAMES = dict((i + 1, s) for (i, s) in enumerate([
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']))

_LOGGING_LEVELS = [logging.ERROR, logging.INFO, logging.DEBUG]


def _main():
    
    args = _parse_args()
    
    if _check_args(args):
        
        level = _LOGGING_LEVELS[args.verbosity]
        logging.basicConfig(level=level)
        
        archive = None if args.dry_run else Archive(args.dest_dir)
        
        visitor = OldBirdDataDirectoryVisitor()
        visitor.visit(args.source_dir, archive, args.year)
    
    
def _parse_args():
    
    parser = argparse.ArgumentParser(
        description='''
            This script creates an NFC archive from a directory containing
            Old Bird NFC data. As the data are processed, messages are
            logged when errors are encountered, and a summary of the
            data is logged at the end. When run with the -d option,
            the script does not create an archive, but still processes all
            of the data, logging the same messages.''')
        
    parser.add_argument(
        '-d', '--dry-run', dest='dry_run', action='store_true', default=False,
        help='process data but do not construct archive')
    
    parser.add_argument(
        '-v', '--verbosity', type=int, choices=xrange(3), default=0,
        help='logging verbosity, either 0, 1, or 2, with 2 most verbose')
    
    parser.add_argument(
        'year', metavar='YEAR', type=int, help='four-digit year of data')
    
    parser.add_argument(
        'source_dir', metavar='SOURCE_DIR', type=str,
        help='path of Old Bird data directory')
    
    parser.add_argument(
        'dest_dir', metavar='DEST_DIR', type=str,
        help='path of new archive directory (must not exist)')
    
    args = parser.parse_args()
    
    return args


def _check_args(args):
    
    if args.year < 1900:
        print('Year {:d} is too small.'.format(args.year), file=sys.stderr)
        return False
    
    if args.year > datetime.datetime.now().year:
        print('Year {:d} is in the future.'.format(args.year), file=sys.stderr)
        return False
    
    if not os.path.exists(args.source_dir):
        format = 'Source directory "{:s}" does not exist.'
        print(format.format(args.source_dir), file=sys.stderr)
        return False
    
    if not args.dry_run and os.path.exists(args.dest_dir):
        format = ('Destination directory "{:s}" exists. Please delete or '
                  'rename it and try again.')
        print(format.format(args.dest_dir), file=sys.stderr)
        return False
    
    return True
    
    
class OldBirdDataDirectoryVisitor(DirectoryVisitor):
    
    
    def visit(self, path, archive, year):
        self.archive = archive
        self.year = year
        level_names = ['root', 'station', 'month', 'day']
        super(OldBirdDataDirectoryVisitor, self).visit(path, level_names)
        
        
    def _start_root_dir_visit(self, path):
        
        self.total_num_files = 0
        self.num_stray_files = 0
        self.num_ignored_dir_files = 0
        self.num_absolute_file_names = 0
        self.num_bad_detector_name_file_names = 0
        self.num_bad_year_file_names = 0
        self.num_relative_file_names = 0
        self.num_malformed_file_names = 0
        
        self.bad_detector_name_dir_paths = set()
        self.bad_year_dir_paths = set()
        self.relative_file_name_dir_paths = set()
        self.malformed_file_name_file_paths = set()
        
        name = os.path.basename(path)
        self._log_info('directory "{:s}"'.format(name))
        
        self._count_stray_files(path)
        
        return True
        
        
    def _count_stray_files(self, path):
        n = _count_clip_files(path, recursive=False)
        if n != 0:
            suffix = 's' if n > 1 else ''
            format = 'Found {:d} stray clip file{:s} in directory "{:s}"'
            self._log_error(format.format(n, suffix, path))
        self.num_stray_files += n
            
            
    def _end_root_dir_visit(self, path):
        
        self.total_num_files += \
            self.num_stray_files + self.num_ignored_dir_files
        
        self._log_error(
            'Total num clip files: {:d}'.format(self.total_num_files))
        
        if self.num_stray_files != 0:
            self._log_error(
                'Num stray clip files: {:d}'.format(self.num_stray_files))
        
        if self.num_ignored_dir_files != 0:
            self._log_error(
                'Num clip files in ignored directories: {:d}'.format(
                    self.num_ignored_dir_files))
        
        if self.num_absolute_file_names != 0:
            self._log_error(
                'Num absolute clip file names: {:d}'.format(
                    self.num_absolute_file_names))
        
        if self.num_bad_detector_name_file_names != 0:
            self._log_error(
                'Num clip file names with bad detector names: {:d}'.format(
                    self.num_bad_detector_name_file_names))
        
        if self.num_bad_year_file_names != 0:
            self._log_error(
                'Num clip file names with bad years: {:d}'.format(
                    self.num_bad_year_file_names))
        
        if self.num_relative_file_names != 0:
            self._log_error(
                'Num relative clip file names: {:d}'.format(
                    self.num_relative_file_names))
        
        if self.num_malformed_file_names != 0:
            self._log_error(
                'Num malformed clip file names: {:d}'.format(
                    self.num_malformed_file_names))
        
        # directories containing file names with bad detector names
        if len(self.bad_detector_name_dir_paths) != 0:
            self._log_error(
                'Paths of directories containing file names with bad '
                'detector names:')
            self._log_paths(self.bad_detector_name_dir_paths)
            
        # directories containing file names with bad years
        if len(self.bad_year_dir_paths) != 0:
            self._log_error(
                'Paths of directories containing file names with bad years:')
            self._log_paths(self.bad_year_dir_paths)
            
        # directories containing relative file names
        if len(self.relative_file_name_dir_paths) != 0:
            self._log_error(
                'Paths of directories containing relative file names:')
            self._log_paths(self.relative_file_name_dir_paths)
        
        # paths of malformed file names
        if len(self.malformed_file_name_file_paths) != 0:
            self._log_error('Paths of malformed file names:')
            self._log_paths(self.malformed_file_name_file_paths)

        
    def _log_paths(self, paths):
        paths = list(paths)
        paths.sort()
        for path in paths:
            self._log_error(path)


    def _start_station_dir_visit(self, path):
        
        name = os.path.basename(path)
        
        name = _STATION_NAME_CORRECTIONS.get(name, name)
        
        if name not in _STATION_NAMES:
            format = 'Ignored unrecognized station directory "{:s}".'
            self._log_error(format.format(path))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.station = name
            self._log_info('    station "{:s}"'.format(self.station))
            self._count_stray_files(path)
            return True
        
        
    def _start_month_dir_visit(self, path):
        
        name = os.path.basename(path)
        month = _MONTH_NUMS.get(name[:3].lower())
        
        if month is None:
            format = 'Ignored unrecognized month directory "{:s}".'
            self._log_error(format.format(path))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.month = month
            format = '        month "{:s}" {:d}'
            self._log_info(format.format(name, self.month))
            self._count_stray_files(path)
            return True
        
        
    def _start_day_dir_visit(self, path):
        
        try:
            self.day = self._get_day(path)
        except:
            pass
        else:
            self._visit_day_dir(path)
            
        return False
        
        
    def _get_day(self, path):
        
        name = os.path.basename(path)
        
        try:
            
            (start_day, end_day) = name.split('-')
            
            start_day = int(start_day)
            
            i = 1 if not end_day[1].isdigit() else 2
            prefix = end_day[i:].lower()
            month = _MONTH_NUMS[prefix[:3]]
            if not _MONTH_NAMES[month].lower().startswith(prefix):
                raise ValueError()
            end_day = int(end_day[:i])
            
        except:
            format = 'Ignored unrecognized day directory "{:s}".'
            self._log_error(format.format(path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise

        if month != self.month:
            format = 'Ignored misplaced or misnamed day directory "{:s}".'
            self._log_error(format.format(path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        if end_day == 1:
            month -= 1

        if start_day < 1:
            format = 'Ignored unrecognized day directory "{:s}".'
            self._log_error(format.format(path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        else:
            
            (_, month_days) = calendar.monthrange(self.year, month)
            
            if start_day > month_days:
                month_name = _MONTH_NAMES[month - 1]
                format = 'Ignored day directory with invalid date "{:s}".'
                self._log_error(format.format(path))
                self.num_ignored_dir_files += _count_clip_files(path)
                raise ValueError()
            
        return start_day
        
        
    def _visit_day_dir(self, path):
        
        name = os.path.basename(path)
        
        format = '            day "{:s}" {:02d}-{:02d}'
        self._log_debug(format.format(name, self.month, self.day))
        
        self._visit_clip_dir(path, [])
        
        
    def _visit_clip_dir(self, path, clip_class_dir_names):
        
        clip_class_name = self._get_clip_class_name(path, clip_class_dir_names)
                    
        n = len(clip_class_dir_names)
        if n != 0:
            indentation = '            ' + ('    ' * n)
            class_name = clip_class_name
            if class_name is None:
                class_name = '<None>'
            dir_name = os.path.basename(path)
            format = '{:s}clip class {:d} "{:s}" {:s}'
            self._log_debug(
                format.format(indentation, n, dir_name, class_name))
                
        for _, subdir_names, file_names in os.walk(path):
            
            file_names = [n for n in file_names if _is_clip_file_name(n)]
            
            for file_name in file_names:
                if _is_clip_file_name(file_name):
                    file_path = os.path.join(path, file_name)
                    self._visit_clip_file(file_path, clip_class_name)
                    
            for subdir_name in subdir_names:
                
                subdir_path = os.path.join(path, subdir_name)
                
                name = subdir_name.lower()
                name = _CLIP_CLASS_DIR_NAME_CORRECTIONS.get(name, name)
                
                self._visit_clip_dir(
                    subdir_path, clip_class_dir_names + [name])
                
            # stop walk from visiting subdirectories
            del subdir_names[:]
            
            
    def _get_clip_class_name(self, path, clip_class_dir_names):
        
        if len(clip_class_dir_names) == 0:
            return None
        
        try:
            return _CLIP_CLASS_NAMES[clip_class_dir_names[-1]]
        
        except KeyError:
            format = 'Unrecognized clip class directory name at "{:s}".'
            self._log_error(format.format(path))
            return None
            
            
    def _visit_clip_file(self, path, clip_class_name):
        
        dir_path, file_name = os.path.split(path)
        
        try:
            (detector_name, time) = \
                file_name_utils.parse_clip_file_name(file_name)
                
        except ValueError:
            
            try:
                (detector_name, time) = \
                    file_name_utils.parse_relative_clip_file_name(file_name)
                    
            except ValueError:
                self.num_malformed_file_names += 1  
                self.malformed_file_name_file_paths.add(path)
                              
            else:
                self.num_relative_file_names += 1
                self.relative_file_name_dir_paths.add(dir_path)
                
        else:
            
            if detector_name not in _DETECTOR_NAMES:
                self.num_bad_detector_name_file_names += 1
                self.bad_detector_name_dir_paths.add(dir_path)
                
            elif time.year != self.year:
                self.num_bad_year_file_names += 1
                self.bad_year_dir_paths.add(dir_path)
                
            else:
                self.num_absolute_file_names += 1
                # TODO: Copy file if indicated.
            
        self.total_num_files += 1
                    
    
    def _log_debug(self, message):
        logging.debug(message)
        
        
    def _log_info(self, message):
        logging.info(message)
        
        
    def _log_error(self, message):
        logging.error(message)


def _count_clip_files(dir_path, recursive=True):
    count = 0
    for dir_path, subdir_names, file_names in os.walk(dir_path):
        for name in file_names:
            if _is_clip_file_name(name):
                count += 1
        if not recursive:
            del subdir_names[:]
    return count


def _is_clip_file_name(name):
    return name.endswith(WAVE_FILE_NAME_EXTENSION)


if __name__ == '__main__':
    _main()
