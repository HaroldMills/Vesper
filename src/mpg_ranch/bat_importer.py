"""Module containing class `BatImporter`."""


from __future__ import print_function

import datetime
import logging
import os
import re

import pytz

from vesper.util.audio_file_utils import WAVE_FILE_NAME_EXTENSION
from vesper.util.bunch import Bunch
import vesper.util.sound_utils as sound_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils
import vesper.vcl.vcl_utils as vcl_utils


_identity = lambda s: s
_capitalize = lambda s: s.capitalize()
_parse_date = time_utils.parse_date
_parse_date6 = lambda mm, dd, yy: _parse_date(yy, mm, dd)
_parse_time = time_utils.parse_time
_parse_dur = time_utils.parse_time_delta


_HELP = '''
<keyword arguments>

Imports MPG Ranch bat clips into an archive.
'''.strip()


_ARGS = '''
- name: --input-dir
  required: true
  value description: directory path
  documentation: |
      The directory containing the data to import.
'''

# Station names from 2015-09-05 email message from Debbie Leick:
#     Clubhouse
#     Pump Slough
#     SC Tank
#     NFP Pool
#     Sage Cairn
#     Sage SC


_STATION_NAMES = {
    'tcpond': 'TC Pond'          
}

_DATE_RE = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
_TIME_RE = re.compile(r'^(\d{2})(\d{2})(\d{2})$')

# We assume that the time zone is US/Mountain for all times that occur
# in input file names.
_TIME_ZONE = pytz.timezone('US/Mountain')


class BatImporter(object):
    
    """Importer for MPG Ranch bat clips."""
    
    
    name = "MPG Ranch Bat Importer"
    
    
    arg_descriptors = \
        vcl_utils.parse_command_args_yaml(_ARGS) + \
        vcl_utils.ARCHIVE_ARG_DESCRIPTORS

    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(BatImporter.name)
        args_help = vcl_utils.create_command_args_help(
            BatImporter.arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        super(BatImporter, self).__init__()
        self._input_dir_path = vcl_utils.get_required_keyword_arg(
            'input-dir', keyword_args)
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)

    
    def import_(self):
        
        archive = vcl_utils.open_archive(self._archive_dir_path)
        self._archive = archive
        
        self._indent_level = 0
        self._indent_size = 4
        self._indentation = ''
        
        self._station_names = frozenset(s.name for s in archive.stations)
        self._capitalized_station_names = dict(
            (name.lower, name) for name in self._station_names)

        self._num_parsed_file_paths = 0
        self._bad_file_paths = set()
        self._unreadable_file_paths = set()
        self._num_add_errors = 0
        
        self._encountered_station_names = set()
        
        dir_names = [os.path.basename(self._input_dir_path)]
        self._walk(self._input_dir_path, dir_names)
        
        self.log_summary()
        
        return True
        
        
    def _walk(self, dir_path, dir_names):
        
        for _, subdir_names, file_names in os.walk(dir_path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                self._visit_file(file_path, dir_names, file_name)
                    
            for subdir_name in subdir_names:
                
                subdir_path = os.path.join(dir_path, subdir_name)
                names = dir_names + [subdir_name]
                
                if subdir_name.lower() == 'noise':
                    logging.info(
                        'Ignoring noise directory "{}".'.format(subdir_path))
                    
                else:
                    
                    self._visit_dir(subdir_path, names)
                
                    self._increase_indentation()
                    self._walk(subdir_path, names)
                    self._decrease_indentation()
                
            # stop os.walk from visiting subdirectories
            del subdir_names[:]


    def _increase_indentation(self):
        self._increment_indentation(1)
        
        
    def _increment_indentation(self, i):
        self._indent_level += i
        n = self._indent_level * self._indent_size
        self._indentation = ' ' * n
        
        
    def _decrease_indentation(self):
        self._increment_indentation(-1)
        
        
    def _indent(self, s):
        return self._indentation + s
    
    
    def _visit_file(self, file_path, dir_names, file_name):
        
        if not file_name.endswith(WAVE_FILE_NAME_EXTENSION):
            return
        
        try:
            info = self._parse_file_name(file_name)
            
        except ValueError:
            logging.error(
                'Could not parse file name "{}" at path "{}".'.format(
                    file_name, file_path))
            self._bad_file_paths.add(file_path)
        
        else:
            
            self._num_parsed_file_paths += 1
            
            try:
                _ = self._archive.get_station(info.station_name)
            except ValueError as e:
                self._handle_add_error(file_path, str(e))
                return
            
            self._encountered_station_names.add(info.station_name)
            
            sound = self._get_clip_sound(file_path)
            if sound is None:
                return
             
            detector_name = 'KPro'
            clip_class_name = 'Call'
              
            try:
                self._archive.add_clip(
                    info.station_name, detector_name, info.start_time,
                    sound, clip_class_name)
              
            except Exception as e:
                self._handle_add_error(file_path, str(e))

            logging.info('Archived clip "{}".'.format(file_path))
            

    def _parse_file_name(self, file_name):
        
        parts = file_name[:-len(WAVE_FILE_NAME_EXTENSION)].split('_')
        
        if len(parts) < 5:
            raise ValueError()
            
        num_station_name_parts = len(parts) - 4
        station_name_parts = parts[:num_station_name_parts]
        other_parts = parts[num_station_name_parts:]
        
        station_name = self._parse_station_name(station_name_parts)
        _parse_digits(other_parts[0], 1)
        start_time = _parse_start_time(other_parts[1], other_parts[2])
        _parse_digits(other_parts[3], 3)
        
        return Bunch(
            station_name=station_name,
            start_time=start_time)
        
        
    def _parse_station_name(self, parts):
        name = '_'.join(parts)
        name = name.lower()
        try:
            return _STATION_NAMES[name]
        except KeyError:
            try:
                return self._capitalized_station_names[name]
            except KeyError:
                raise ValueError()

    
    def _handle_add_error(self, file_path, message):
        m = self._indent('Error adding clip from "{}": {}')
        logging.error(m.format(self._rel(file_path), message))
        self._num_add_errors += 1
            

    def _get_clip_sound(self, file_path):
        
        try:
            return sound_utils.read_sound_file(file_path)
            
        except Exception:
            logging.error(
                'Could not read sound file at "{}".'.format(file_path))
            self._unreadable_file_paths.add(file_path)
            return None
    
    
    def _rel(self, path):
        return path[len(self._input_dir_path) + 1:]
    
    
    def _visit_dir(self, dir_path, dir_names):
        logging.info(self._indent('dir "{:s}"'.format(dir_names[-1])))
        
        
    def log_summary(self):
        
        sfp = self._show_file_path
        
        logging.info('')
        self._show_items(
            'File names that could not be parsed:', self._bad_file_paths, sfp)
        
        logging.info('')
        self._show_items('Unreadable files:', self._unreadable_file_paths, sfp)
        
        logging.info('')
        self._show_items('Station names:', self._encountered_station_names)
        
        logging.info('')
        
        logging.info(
            '{} file names were parsed'.format(self._num_parsed_file_paths))
        logging.info(
            '{} file names could not be parsed'.format(
                len(self._bad_file_paths)))
        logging.info(
            '{} clip add operations failed'.format(self._num_add_errors))
        

    def _show_items(self, title, items, show=None):
        
        if show is None:
            show = self._show_item
            
        logging.info(title)
        
        items = sorted(items)
        
        self._increase_indentation()
        
        if len(items) == 0:
            logging.info(self._indent('None'))
            
        else:
            for item in items:
                show(item)
            
        self._decrease_indentation()


    def _show_item(self, item):
        logging.info(self._indent(str(item)))
        
        
    def _show_file_path(self, path):
        (dir_path, file_name) = os.path.split(path)
        message = self._indent('{} ({})'.format(file_name, dir_path))
        logging.info(message)


def _parse_digits(s, n):
    if len(s) != n or not s.isdigit():
        raise ValueError()

    
def _parse_start_time(d, t):
    
    m = _DATE_RE.match(d)
    
    if m is None:
        raise ValueError()
    
    start_date = time_utils.parse_date(*m.groups())
    
    m = _TIME_RE.match(t)
    
    if m is None:
        raise ValueError()
    
    start_time = time_utils.parse_time(*m.groups())
    
    dt = datetime.datetime.combine(start_date, start_time)
    
    # We don't worry here about the possibility of ambiguous or
    # nonexistent local times. Those will raise exceptions.
    return time_utils.create_utc_datetime(
        dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second,
        time_zone=_TIME_ZONE)

