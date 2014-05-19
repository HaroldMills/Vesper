"""Creates a clip archive from Old Bird clip directories."""


from __future__ import print_function

from collections import defaultdict
import argparse
import calendar
import datetime
import logging
import os
import sys

from nfc.archive.archive import Archive
from nfc.util.audio_file_utils import WAVE_FILE_NAME_EXTENSION
from nfc.util.bunch import Bunch
from nfc.util.directory_visitor import DirectoryVisitor
import nfc.util.sound_utils as sound_utils
import old_bird.file_name_utils as file_name_utils


_STATION_NAME_CORRECTIONS = {
    'AJO': 'Ajo'
}

_STATION_NAMES = frozenset([
    'Ajo', 'Alfred', 'ColumbiaLC', 'Danby', 'Derby', 'HSHS', 'Jamestown',
    'LTU', 'Minatitlan', 'NMHS', 'Oneonta', 'Ottawa', 'Skinner', 'WFU'])

_STATION_NAMES = frozenset(['Ajo'])

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
'''set of clip class names'''
    
_CLIP_CLASS_NAMES_DICT = dict(
    [(n.split('.')[-1].lower(), n) for n in _CLIP_CLASS_NAMES] +
    [('classified', 'Call'), ('unclassified', None)])
'''mapping from lower case clip class directory names to clip class names'''

_MONTH_PREFIXES = [
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

_MONTH_NUMS = dict((s, i + 1) for (i, s) in enumerate(_MONTH_PREFIXES))

_MONTH_PREFIXES = frozenset(_MONTH_PREFIXES)

_MONTH_NAMES = dict((i + 1, s) for (i, s) in enumerate([
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December']))

_DST_END_TIMES = [datetime.datetime(*t) for t in [
    (2012, 11, 4, 2)
]]

_LOGGING_LEVELS = [logging.ERROR, logging.INFO, logging.DEBUG]


def _main():
    
    args = _parse_args()
    
    if _check_args(args):
        
        level = _LOGGING_LEVELS[args.verbosity]
        logging.basicConfig(level=level)
        
        archive = _create_archive(args)
        
        visitor = OldBirdDataDirectoryVisitor()
        visitor.visit(args.source_dir, archive, args.year)
    
    
def _parse_args():
    
    parser = argparse.ArgumentParser(
        description='''
            This script creates an NFC archive from a directory containing
            Old Bird NFC data. As the data are processed, messages are
            logged as errors are encountered, and a summary of the
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
    
    
def _create_archive(args):
    
    if args.dry_run:
        return None
    
    else:
        
        stations = _create_bunches(_STATION_NAMES)
        detectors = _create_bunches(_DETECTOR_NAMES)
        clip_class_names = _create_bunches(_CLIP_CLASS_NAMES)

        os.makedirs(args.dest_dir)
        
        return Archive.create(
                   args.dest_dir, stations, detectors, clip_class_names)


def _create_bunches(names):
    names = list(names)
    names.sort()
    return [Bunch(name=name) for name in names]


class OldBirdDataDirectoryVisitor(DirectoryVisitor):
    
    
    def visit(self, path, archive, year):
        self.root_path = path
        self.archive = archive
        self.year = year
        level_names = ['root', 'station', 'month', 'day']
        super(OldBirdDataDirectoryVisitor, self).visit(path, level_names)
        
        
    def _start_root_dir_visit(self, path):
        
        self.total_num_files = 0
        self.num_escaped_files = 0
        self.num_ignored_dir_files = 0
        self.num_absolute_file_names = 0
        self.num_bad_detector_name_file_names = 0
        self.num_misplaced_files = 0
        self.num_relative_file_names = 0
        self.num_malformed_file_names = 0
        self.num_dst_ambiguity_files = 0
        self.num_unreadable_files = 0
        self.num_add_errors = 0
        self.num_duplicate_files = 0
        self.num_reclassified_files = 0
        
        self.bad_detector_name_dir_paths = set()
        self.misplaced_file_counts = defaultdict(int)
        self.relative_file_name_dir_paths = set()
        self.malformed_file_name_file_paths = set()
        self.dst_ambiguity_file_counts = defaultdict(int)
        self.reclassifications = set()
        
        self.dst_ambiguity_bounds = self._init_dst_ambiguity_bounds()
        
        self.clip_info = {}
        
        self._log_info('directory "{:s}"'.format(path))
        
        self._count_escaped_files(path)
        
        return True
        
        
    def _init_dst_ambiguity_bounds(self):
        one_hour = datetime.timedelta(hours=1)
        return dict((time.year, (time - one_hour, time))
                    for time in _DST_END_TIMES)
            
        
    def _count_escaped_files(self, path):
        n = _count_clip_files(path, recursive=False)
        if n != 0:
            suffix = 's' if n > 1 else ''
            format = 'Found {:d} escaped clip file{:s} in directory "{:s}"'
            self._log_error(format.format(n, suffix, self._rel(path)))
        self.num_escaped_files += n
            
            
    def _end_root_dir_visit(self, path):
        
        self._log_space()
        
        self.total_num_files += \
            self.num_escaped_files + self.num_ignored_dir_files
        
        self._log_error(
            'Total num clip files: {:d}'.format(self.total_num_files))
        
        if self.num_escaped_files != 0:
            self._log_error(
                'Num escaped clip files: {:d}'.format(self.num_escaped_files))
        
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
        
        if self.num_misplaced_files != 0:
            self._log_error(
                'Num misplaced clip files: {:d}'.format(
                    self.num_misplaced_files))
        
        if self.num_relative_file_names != 0:
            self._log_error(
                'Num relative clip file names: {:d}'.format(
                    self.num_relative_file_names))
        
        if self.num_malformed_file_names != 0:
            self._log_error(
                'Num malformed clip file names: {:d}'.format(
                    self.num_malformed_file_names))
        
        if self.num_dst_ambiguity_files != 0:
            self._log_error(
                ('Num clip files with ambiguous times near DST end: '
                 '{:d}').format(self.num_dst_ambiguity_files))
            
        if self.num_unreadable_files != 0:
            self._log_error(
                'Num unreadable clip files: {:d}'.format(
                    self.num_unreadable_files))
            
        if self.num_add_errors != 0:
            self._log_error(
                'Num archive add errors: {:d}'.format(
                    self.num_add_errors))
            
        if self.num_duplicate_files != 0:
            self._log_error(
                'Num duplicate clip files: {:d}'.format(
                    self.num_duplicate_files))
            
        if self.num_reclassified_files != 0:
            self._log_error(
                'Num reclassified clip files: {:d}'.format(
                    self.num_reclassified_files))
            
        # directories containing file names with bad detector names
        if len(self.bad_detector_name_dir_paths) != 0:
            self._log_paths(
                ('Paths of directories containing file names with bad '
                 'detector names'),
                self.bad_detector_name_dir_paths)
            
        # directories containing misplaced files
        if self.num_misplaced_files != 0:
            self._log_misplaced_file_dir_paths()
            
        # directories containing relative file names
        if len(self.relative_file_name_dir_paths) != 0:
            self._log_paths(
                'Paths of directories containing relative file names',
                self.relative_file_name_dir_paths)
        
        # paths of malformed file names
        if len(self.malformed_file_name_file_paths) != 0:
            self._log_paths(
                'Paths of malformed file names',
                self.malformed_file_name_file_paths)
            
        # directories containing files with ambiguous times near DST end
        if self.num_dst_ambiguity_files != 0:
            self._log_dst_ambiguity_dir_paths()
            
        # files that have two or more incompatible classifications
        if len(self.reclassifications) != 0:
            self._log_path_pairs('Reclassified files:', self.reclassifications)

        
    def _log_space(self):
        for _ in xrange(5):
            self._log_error('')
            
            
    def _log_paths(self, message, paths):
        
        self._log_space()
        
        self._log_error(message)
            
        paths = [self._rel(p) for p in paths]
        paths.sort()
        for path in paths:
            self._log_error(path)
            
            
    def _log_misplaced_file_dir_paths(self):
        
        paths = self.misplaced_file_counts.keys()
        
        if len(paths) != 0:
            
            self._log_space()
            
            self._log_error(
                'Paths of directories containing misplaced clip files:')
            
            paths.sort()  
                      
            for path in paths:
                
                num_misplaced_files = self.misplaced_file_counts[path]
                total_num_files = _count_clip_files(path, recursive=False)
                
                self._log_error(
                    '{:s} ({:d} of {:d} files)'.format(
                        self._rel(path), num_misplaced_files, total_num_files))
            
            
    def _log_dst_ambiguity_dir_paths(self):

        self._log_space()
        
        self._log_error(
            'Paths of directories containing clip files with ambiguous '
            'times near DST end:')
        
        pairs = self.dst_ambiguity_file_counts.items()
        pairs.sort()
        for path, count in pairs:
            self._log_error('{:s} ({:d} files)'.format(self._rel(path), count))


    def _log_path_pairs(self, message, pairs):
        
        self._log_space()
        
        self._log_error(message)
        
        pairs = [(self._rel(p), self._rel(q)) for p, q in pairs]
        pairs.sort()
        for pair in pairs:
            self._log_error(pair)


    def _start_station_dir_visit(self, path):
        
        name = os.path.basename(path)
        
        name = _STATION_NAME_CORRECTIONS.get(name, name)
        
        if name not in _STATION_NAMES:
            format = 'Ignored unrecognized station directory "{:s}".'
            self._log_error(format.format(self._rel(path)))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.station_name = name
            self._log_info('    station "{:s}"'.format(self.station_name))
            self._count_escaped_files(path)
            return True
        
        
    def _start_month_dir_visit(self, path):
        
        name = os.path.basename(path)
        month = _MONTH_NUMS.get(name[:3].lower())
        
        if month is None:
            format = 'Ignored unrecognized month directory "{:s}".'
            self._log_error(format.format(self._rel(path)))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.month = month
            format = '        month "{:s}" {:d}'
            self._log_info(format.format(name, self.month))
            self._count_escaped_files(path)
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
        rel_path = self._rel(path)
        
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
            self._log_error(format.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise

        if month != self.month:
            format = 'Ignored misplaced or misnamed day directory "{:s}".'
            self._log_error(format.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        if start_day < 1:
            format = 'Ignored unrecognized day directory "{:s}".'
            self._log_error(format.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        else:
            
            start_month = month if end_day != 1 else month - 1

            (_, month_days) = calendar.monthrange(self.year, start_month)
            
            if start_day > month_days:
                format = 'Ignored day directory with invalid date "{:s}".'
                self._log_error(format.format(rel_path))
                self.num_ignored_dir_files += _count_clip_files(path)
                raise ValueError()
            
        self.night = Archive.get_night(
            datetime.datetime(self.year, self.month, end_day, 0, 0, 0))
        
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
            
            for file_name in file_names:
                if file_name_utils.is_clip_file_name(file_name):
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
            return _CLIP_CLASS_NAMES_DICT[clip_class_dir_names[-1]]
        
        except KeyError:
            format = 'Unrecognized clip class directory name at "{:s}".'
            self._log_error(format.format(self._rel(path)))
            return None
            
            
    def _rel(self, path):
        return path[len(self.root_path) + 1:]
    
    
    def _visit_clip_file(self, path, clip_class_name):
        
        dir_path, file_name = os.path.split(path)
        
        try:
            (detector_name, time) = \
                file_name_utils.parse_absolute_clip_file_name(file_name)
                
        except ValueError:
            
            try:
                (detector_name, time) = \
                    file_name_utils.parse_relative_clip_file_name(file_name)
                    
            except ValueError:
                self.num_malformed_file_names += 1  
                self.malformed_file_name_file_paths.add(path)
                              
            else:
                # successfully parsed relative file name
                self.num_relative_file_names += 1
                self.relative_file_name_dir_paths.add(dir_path)
                
        else:
            # successfully parsed absolute file name
            
            if detector_name not in _DETECTOR_NAMES:
                self.num_bad_detector_name_file_names += 1
                self.bad_detector_name_dir_paths.add(dir_path)
                
            elif Archive.get_night(time) != self.night:
                self.num_misplaced_files += 1
                self.misplaced_file_counts[dir_path] += 1
                
            else:
                # have clip station name, detector name, and time
                
                self.num_absolute_file_names += 1
                
                self._visit_clip_file_aux(
                    path, self.station_name, detector_name, time,
                    clip_class_name)
            
        self.total_num_files += 1
                    
    
    def _visit_clip_file_aux(
        self, path, station_name, detector_name, time, clip_class_name):
        
        if self._is_dst_ambiguous(time):
            self.num_dst_ambiguity_files += 1
            dir_path = os.path.dirname(path)
            self.dst_ambiguity_file_counts[dir_path] += 1
            
        key = (station_name, detector_name, time)
        
        try:
            clip = self.clip_info[key]
        
        except KeyError:
            # do not already have clip for this station, detector, and time
            
            if self.archive is None:
                # no archive (dry run)
                
                self.clip_info[key] = Bunch(
                    station_name=station_name,
                    detecto_name=detector_name,
                    time=time,
                    clip_class_name=clip_class_name,
                    path=path)
                
            else:
                # have archive
                
                try:
                    sound = sound_utils.read_sound_file(path)
                    
                except Exception, e:
                    format = 'Error reading sound file "{:s}": {:s}'
                    self._log_error(format.format(self._rel(path), str(e)))
                    self.num_unreadable_files += 1
                
                else:
                    # successfully read sound file
                
                    try:
                        clip = self.archive.add_clip(
                            station_name, detector_name, time, sound,
                            clip_class_name)
                        clip.path = path
                    
                    except Exception, e:
                        format = 'Error adding clip from "{:s}": {:s}'
                        self._log_error(format.format(self._rel(path), str(e)))
                        self.num_add_errors += 1
                    
                    else:
                        self.clip_info[key] = clip
            
        else:
            # already have clip for this station, detector, and time
            
            old = clip.clip_class_name
            new = clip_class_name
            
            if new != old:
                
                if old is None or \
                   new is not None and \
                   new.startswith(old) and \
                   new[len(old)] == '.':
                    # new classification is more specific version of old one
                
                    clip.clip_class_name = new
                    
                else:
                    # new classification differs from old one and is not
                    # a more specific version of it
                    
                    self.reclassifications.add((clip.path, path))
                    self.num_reclassified_files += 1
                    
                clip.path = path
                
            self.num_duplicate_files += 1
        
    
    def _is_dst_ambiguous(self, time):
        
        bounds = self.dst_ambiguity_bounds.get(time.year)
        
        if bounds is None:
            return False
        
        else:
            start_time, end_time = bounds
            return time >= start_time and time < end_time
               
               
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
            if file_name_utils.is_clip_file_name(name):
                count += 1
        if not recursive:
            del subdir_names[:]
    return count


if __name__ == '__main__':
    _main()
