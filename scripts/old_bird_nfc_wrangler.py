"""Creates a clip archive from Old Bird clip directories."""


from __future__ import print_function

from collections import defaultdict
import argparse
import calendar
import datetime
import logging
import os
import sys
import time

from nfc.archive.archive import Archive
from nfc.archive.clip_class import ClipClass
from nfc.archive.detector import Detector
from nfc.archive.dummy_archive import DummyArchive
from nfc.archive.station import Station
from nfc.util.bunch import Bunch
from nfc.util.directory_visitor import DirectoryVisitor
from old_bird.wrangler_time_keeper import (
    WranglerTimeKeeper, NonexistentTimeError, AmbiguousTimeError)
import nfc.archive.archive_utils as archive_utils
import nfc.util.sound_utils as sound_utils
import old_bird.file_name_utils as file_name_utils


_STATIONS = [Station(*t) for t in [
    ('Ajo', 'Ajo High School', 'US/Arizona'),
    ('Alfred', 'Klingensmith Residence', 'US/Eastern'),
    ('CLC', 'Columbia Land Conservancy', 'US/Eastern'),
    ('Danby', 'Evans Residence', 'US/Eastern'),
    ('DHBO', 'Derby Hill Bird Observatory', 'US/Eastern'),
    ('HHSS', 'Harlingen High School South', 'US/Central'),
    ('JAS', 'Jamestown Audubon Society', 'US/Eastern'),
    ('LTU', 'Louisiana Technical University', 'US/Central'),
    ('Minatitlan',
     u'Minatitl\u00E1n/Coatzacoalcos International Airport',
     'America/Mexico_City'),
    ('NMHS', 'North Manchester High School', 'US/Eastern'),
    ('Oneonta', 'Oneonta Municipal Airport', 'US/Eastern'),
    ('ONWR', 'Ottawa National Wildlife Refuge', 'US/Eastern'),
    ('Skinner', 'Skinner State Park', 'US/Eastern'),
    ('WFU', 'Wake Forest University', 'US/Eastern')
]]


_EXCLUDED_STATION_NAMES = frozenset(['Danby', 'LTU', 'Minatitlan'])

_MONITORING_TIME_ZONE_NAMES = {}
"""
See documentation for the `WranglerTimeKeeper` initializer `time_zone_names`
parameter.
"""

_MONITORING_START_TIMES = {
    2012: {
        'Alfred': ('21:00:00', ['10-3']),
        'DHBO': ('21:00:00', [('5-11', '5-12'), ('5-28', '6-6')]),
        'JAS': ('21:00:00', [('8-17', '8-19')]),
        'Oneonta': ('21:00:00', []),
        'ONWR': ('20:00:00', ['9-04', '9-17']),
        'Skinner': ('21:00:00',
                    ['8-13', '8-14', ('10-6', '10-12'), ('10-14', '10-25')])
    }
}
"""
See documentation for the `WranglerTimeKeeper` initializer `start_times`
parameter.
"""


_DETECTORS = [Detector('Tseep')]

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

_CLIP_CLASS_NAMES = \
    ['Call', 'Noise', 'Tone'] + ['Call.' + n for n in _CALL_CLIP_CLASS_NAMES]
_CLIP_CLASS_NAMES.sort()
_CLIP_CLASSES = [ClipClass(name) for name in _CLIP_CLASS_NAMES]
    
_CLIP_CLASS_NAMES_DICT = dict(
    [(n.split('.')[-1].lower(), n) for n in _CLIP_CLASS_NAMES] +
    [('classified', 'Call')])
'''mapping from lower case clip class directory names to clip class names'''

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
        
        archive = _create_archive(args)
        
        visitor = _OldBirdDataDirectoryVisitor()
        visitor.visit(args.source_dir, archive, args.year, args.dry_run)
    
    
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
        f = 'Source directory "{:s}" does not exist.'
        print(f.format(args.source_dir), file=sys.stderr)
        return False
    
    if not args.dry_run and os.path.exists(args.dest_dir):
        f = ('Destination directory "{:s}" exists. Please delete or '
             'rename it and try again.')
        print(f.format(args.dest_dir), file=sys.stderr)
        return False
    
    return True
    
    
def _create_archive(args):
    archive_class = DummyArchive if args.dry_run else Archive
    return archive_class.create(
        args.dest_dir, _STATIONS, _DETECTORS, _CLIP_CLASSES)


class _OldBirdDataDirectoryVisitor(DirectoryVisitor):
    
    
    def visit(self, path, archive, year, dry_run=False):
        
        self.root_path = path
        self.archive = archive
        self.stations = dict((s.name, s) for s in self.archive.stations)
        self.detectors = dict((d.name, d) for d in self.archive.detectors)
        self.year = year
        self.dry_run = dry_run
        
        level_names = ['root', 'station', 'month', 'day']
        super(_OldBirdDataDirectoryVisitor, self).visit(path, level_names)
        
        
    def _start_root_dir_visit(self, path):
        
        self.total_num_files = 0
        
        self.num_escaped_files = 0
        self.num_ignored_dir_files = 0
        
        self.num_date_time_file_names = 0
        self.num_resolved_file_names = 0
        self.num_unresolved_file_names = 0
        self.num_malformed_file_names = 0
        
        self.num_misplaced_files = 0
        self.num_bad_detector_name_file_names = 0
        self.num_nonexistent_time_files = 0
        self.num_ambiguous_time_files = 0
        self.num_duplicate_files = 0
        self.num_reclassified_files = 0
        self.num_unreadable_files = 0
        self.num_add_errors = 0
        
        self.unresolved_file_name_dir_paths = set()
        self.malformed_file_name_file_paths = set()
        self.misplaced_file_counts = defaultdict(int)
        self.bad_detector_name_dir_paths = set()
        self.nonexistent_time_file_counts = defaultdict(int)
        self.ambiguous_time_file_counts = defaultdict(int)
        self.reclassifications = set()
        
        self.time_keeper = WranglerTimeKeeper(
            self.stations, _MONITORING_TIME_ZONE_NAMES,
            _MONITORING_START_TIMES)
        
        self.resolved_times = {}
        
        self.clip_info = {}
        
        self._log_info('directory "{:s}"'.format(path))
        
        self.start_time = time.time()
        self._log_clip_count(0)
        
        self._count_escaped_files(path)
        
        return True
        
        
    def _count_escaped_files(self, path):
        n = _count_clip_files(path, recursive=False)
        if n != 0:
            suffix = 's' if n > 1 else ''
            f = 'Found {:d} escaped clip file{:s} in directory "{:s}"'
            self._log_error(f.format(n, suffix, self._rel(path)))
        self.num_escaped_files += n
            
            
    def _log_clip_count(self, num_clips):
        return
#         seconds = int(round(time.time() - self.start_time))
#         f = 'processed {:d} clips at {:d} seconds'
#         self._log_info(f.format(num_clips, seconds))
                    
    
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
        
        if self.num_date_time_file_names != 0:
            self._log_error(
                'Num date/time clip file names: {:d}'.format(
                    self.num_date_time_file_names))
        
        if self.num_resolved_file_names != 0:
            self._log_error(
                'Num resolved elapsed time clip file names: {:d}'.format(
                    self.num_resolved_file_names))
        
        if self.num_unresolved_file_names != 0:
            self._log_error(
                'Num unresolved elapsed time clip file names: {:d}'.format(
                    self.num_unresolved_file_names))
        
        if self.num_malformed_file_names != 0:
            self._log_error(
                'Num malformed clip file names: {:d}'.format(
                    self.num_malformed_file_names))
        
        self._log_space()
        
        if self.num_misplaced_files != 0:
            self._log_error(
                'Num misplaced clip files: {:d}'.format(
                    self.num_misplaced_files))
        
        if self.num_bad_detector_name_file_names != 0:
            self._log_error(
                'Num clip file names with bad detector names: {:d}'.format(
                    self.num_bad_detector_name_file_names))
        
        if self.num_nonexistent_time_files != 0:
            self._log_error(
                ('Num clip files with nonexistent times near DST start: '
                 '{:d}').format(self.num_nonexistent_time_files))
            
        if self.num_ambiguous_time_files != 0:
            self._log_error(
                ('Num clip files with ambiguous times near DST end: '
                 '{:d}').format(self.num_ambiguous_time_files))
            
        if self.num_duplicate_files != 0:
            self._log_error(
                'Num duplicate clip files: {:d}'.format(
                    self.num_duplicate_files))
            
        if self.num_reclassified_files != 0:
            self._log_error(
                'Num reclassified clip files: {:d}'.format(
                    self.num_reclassified_files))
            
        if self.num_unreadable_files != 0:
            self._log_error(
                'Num unreadable clip files: {:d}'.format(
                    self.num_unreadable_files))
            
        if self.num_add_errors != 0:
            self._log_error(
                'Num archive add errors: {:d}'.format(
                    self.num_add_errors))
            
        # directories containing elapsed time file names
        if len(self.unresolved_file_name_dir_paths) != 0:
            self._log_paths(
                ('Paths of directories containing unresolved elapsed time '
                 'file names:'), self.unresolved_file_name_dir_paths)
            
        # revsolved times
        if len(self.resolved_times) != 0:
            self._log_resolved_times()
        
        # paths of malformed file names
        if len(self.malformed_file_name_file_paths) != 0:
            self._log_paths(
                'Paths of malformed file names:',
                self.malformed_file_name_file_paths)
            
        # directories containing misplaced files
        if self.num_misplaced_files != 0:
            self._log_misplaced_file_dir_paths()
            
        # directories containing file names with bad detector names
        if len(self.bad_detector_name_dir_paths) != 0:
            self._log_paths(
                ('Paths of directories containing file names with bad '
                 'detector names:'),
                self.bad_detector_name_dir_paths)
            
        # directories containing files with nonexistent times near DST start
        if self.num_nonexistent_time_files != 0:
            self._log_nonexistent_time_dir_paths()
            
        # directories containing files with ambiguous times near DST end
        if self.num_ambiguous_time_files != 0:
            self._log_ambiguous_time_dir_paths()
            
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
            
            
    def _log_resolved_times(self):
        
        self._log_space()
        
        self._log_error('Examples of resolved times:')
        
        keys = self.resolved_times.keys()
        keys.sort()
        
        for key in keys:
            
            station_name, night = key
            delta_time, time = self.resolved_times[key]
            
            self._log_error(
                station_name + ' ' + str(night) + ': ' + str(delta_time) +
                ' ' + str(time))
            
            
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
            
            
    def _log_nonexistent_time_dir_paths(self):
        self._log_bad_time_dir_paths('nonexistent', 'start')


    def _log_bad_time_dir_paths(self, name, point):
        
        self._log_space()
        
        self._log_error(
            ('Paths of directories containing clip files with {:s} '
             'times near DST {:s}:').format(name, point))
        
        name = '{:s}_time_file_counts'.format(name)
        counts = getattr(self, name)
        pairs = counts.items()
        pairs.sort()
        for path, count in pairs:
            self._log_error('{:s} ({:d} files)'.format(self._rel(path), count))


    def _log_ambiguous_time_dir_paths(self):
        self._log_bad_time_dir_paths('ambiguous', 'end')


    def _log_path_pairs(self, message, pairs):
        
        self._log_space()
        
        self._log_error(message)
        
        pairs = [(self._rel(p), self._rel(q)) for p, q in pairs]
        pairs.sort()
        for pair in pairs:
            self._log_error(pair)


    def _start_station_dir_visit(self, path):
        
        name = os.path.basename(path)
        
        if name in _EXCLUDED_STATION_NAMES or name not in self.stations:
            
            if name in _EXCLUDED_STATION_NAMES:
                s = 'excluded'
            else:
                s = 'unrecognized'
                
            f = 'Ignored {:s} station directory "{:s}".'
            self._log_error(f.format(s, self._rel(path)))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.station = self.stations[name]
            self._log_info('    station "{:s}"'.format(self.station.name))
            self._count_escaped_files(path)
            return True
        
        
    def _start_month_dir_visit(self, path):
        
        name = os.path.basename(path)
        month = _MONTH_NUMS.get(name[:3].lower())
        
        if month is None:
            f = 'Ignored unrecognized month directory "{:s}".'
            self._log_error(f.format(self._rel(path)))
            self.num_ignored_dir_files += _count_clip_files(path)
            return False
        
        else:
            self.month = month
            f = '        month "{:s}" {:d}'
            self._log_info(f.format(name, self.month))
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
            f = 'Ignored unrecognized day directory "{:s}".'
            self._log_error(f.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise

        if month != self.month:
            f = 'Ignored misplaced or misnamed day directory "{:s}".'
            self._log_error(f.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        if start_day < 1:
            f = 'Ignored unrecognized day directory "{:s}".'
            self._log_error(f.format(rel_path))
            self.num_ignored_dir_files += _count_clip_files(path)
            raise ValueError()
        
        else:
            
            start_month = month if end_day != 1 else month - 1

            (_, month_days) = calendar.monthrange(self.year, start_month)
            
            if start_day > month_days:
                f = 'Ignored day directory with invalid date "{:s}".'
                self._log_error(f.format(rel_path))
                self.num_ignored_dir_files += _count_clip_files(path)
                raise ValueError()
            
        # We assume here that day directory names reflect local time,
        # regardless of the monitoring time zone.
        midnight = datetime.datetime(self.year, self.month, end_day, 0, 0, 0)
        self.night = archive_utils.get_night(midnight)
        
        return start_day
        
        
    def _visit_day_dir(self, path):
        
        name = os.path.basename(path)
        
        f = '            day "{:s}" {:02d}-{:02d}'
        self._log_debug(f.format(name, self.month, self.day))
        
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
            f = '{:s}clip class {:d} "{:s}" {:s}'
            self._log_debug(f.format(indentation, n, dir_name, class_name))
                
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
            f = 'Unrecognized clip class directory name at "{:s}".'
            self._log_error(f.format(self._rel(path)))
            return None
            
            
    def _rel(self, path):
        return path[len(self.root_path) + 1:]
    
    
    def _visit_clip_file(self, path, clip_class_name):
        
        dir_path, file_name = os.path.split(path)
        
        try:
            (detector_name, time) = \
                file_name_utils.parse_date_time_clip_file_name(file_name)
                
        except ValueError:
            
            try:
                f = file_name_utils.parse_elapsed_time_clip_file_name
                (detector_name, time_delta) = f(file_name)
                    
            except ValueError:
                self.num_malformed_file_names += 1
                self.malformed_file_name_file_paths.add(path)
                              
            else:
                # successfully parsed elapsed time file name
                
                convert = self.time_keeper.convert_elapsed_time_to_utc
                time = convert(time_delta, self.station.name, self.night)
                
                if time is None:
                    self.num_unresolved_file_names += 1
                    self.unresolved_file_name_dir_paths.add(dir_path)

                else:
                    self.num_resolved_file_names += 1
                    self.resolved_times[(self.station.name, self.night)] = \
                        (time_delta, time)
                    self._visit_clip_file_aux(
                        path, self.station, detector_name, time,
                        clip_class_name)
                
        else:
            # successfully parsed date/time file name
            
            self.num_date_time_file_names += 1
            
            try:
                convert = self.time_keeper.convert_naive_time_to_utc
                time = convert(time, self.station.name)
                
            except NonexistentTimeError:
                self.num_nonexistent_time_files += 1
                self.nonexistent_time_file_counts[dir_path] += 1
            
            except AmbiguousTimeError:
                self.num_ambiguous_time_files += 1
                self.ambiguous_time_file_counts[dir_path] += 1
                
            self._visit_clip_file_aux(
                path, self.station, detector_name, time, clip_class_name)
            
        self.total_num_files += 1
        
        if self.total_num_files % 10000 == 0:
            self._log_clip_count(self.total_num_files)
            
            
    def _visit_clip_file_aux(
        self, path, station, detector_name, time, clip_class_name):
        
        dir_path = os.path.dirname(path)
        
        if station.get_night(time) != self.night:
            self.num_misplaced_files += 1
            self.misplaced_file_counts[dir_path] += 1
            return
            
        if detector_name not in self.detectors:
            self.num_bad_detector_name_file_names += 1
            self.bad_detector_name_dir_paths.add(dir_path)
            return
            
        key = (station.name, detector_name, time)
        
        try:
            clip = self.clip_info[key]
        
        except KeyError:
            # do not already have clip for this station, detector, and time
            
            if self.dry_run:
                
                self.clip_info[key] = Bunch(
                    station_name=station.name,
                    detector_name=detector_name,
                    time=time,
                    clip_class_name=clip_class_name,
                    path=path)
                
            else:
                # not dry run
                
                try:
#                    sound = None
                    sound = sound_utils.read_sound_file(path)
                    
                except Exception, e:
                    f = 'Error reading sound file "{:s}": {:s}'
                    self._log_error(f.format(self._rel(path), str(e)))
                    self.num_unreadable_files += 1
                
                else:
                    # successfully read sound file
                
                    try:
                        clip = self.archive.add_clip(
                            station.name, detector_name, time, sound,
                            clip_class_name)
                        clip.path = path
                    
                    except Exception, e:
                        f = 'Error adding clip from "{:s}": {:s}'
                        self._log_error(f.format(self._rel(path), str(e)))
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
