"""Module containing class `BatImporter`."""


import datetime
import logging
import os
import re

import pandas as pd
import pytz

from vesper.util.audio_file_utils import WAVE_FILE_NAME_EXTENSION
from vesper.vcl.command import CommandSyntaxError
import mpg_ranch.bat_utils as bat_utils
import vesper.util.sound_utils as sound_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils
import vesper.vcl.vcl_utils as vcl_utils


_ALL_CLIP_CLASSES = '*'
_CALL_CLIP_CLASSES = 'Call*'
_SPECIES_CLIP_CLASSES = 'Call.*'
_CLIP_CLASSES_ARG_VALUES = [
    _ALL_CLIP_CLASSES, _CALL_CLIP_CLASSES, _SPECIES_CLIP_CLASSES]


_HELP = '''
<keyword arguments>

Imports MPG Ranch bat clips into an archive.
'''.strip()


_ARGS = '''

- name: --input-dir
  required: true
  value description: directory path
  documentation: |
      The directory containing the clips to import.
      
      This directory must contain a "Spreadsheets" subdirectory,
      and the "Spreadsheets" directory must contain files "id.csv" and
      "tc_pond_5sec_split_sm2enabled_BatchClassify.txt". These files
      must contain species IDs output by Kaleidoscope Pro and
      SonoBat, respectively. This rather arbitrary arrangement is
      only a placeholder, to be replaced in the future with a more
      flexible means of providing Kaleidoscope Pro and SonoBat
      classifications.
      
- name: --clip-classes
  required: false
  value description: clip classes
  documentation: |
      The classes of clips to import. This argument must have one of
      three values, "{}", "{}", and "{}".
      Default: "{}"

'''.format(
    _ALL_CLIP_CLASSES, _CALL_CLIP_CLASSES, _SPECIES_CLIP_CLASSES,
    _CALL_CLIP_CLASSES)


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

_DETECTOR_NAME = 'KPro'

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
        self._included_clip_classes = _parse_clip_classes_arg(keyword_args)
        self._ignore_noise_dirs = False
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)

    
    def import_(self):
        
        self._classifications = self._get_classifications(self._input_dir_path)
        
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
        
        
    def _get_classifications(self, input_dir_path):
        
        df = _get_classifications(input_dir_path)
        return dict(self._get_classification(*t) for t in df.itertuples())
    
    
    def _get_classification(self, index, file_name_base, species_code):
        station_name, start_time = self._parse_file_name_base(file_name_base)
        return ((station_name, start_time), species_code)
            
    
    def _walk(self, dir_path, dir_names):
        
        for _, subdir_names, file_names in os.walk(dir_path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                self._visit_file(file_path, dir_names, file_name)
                    
            for subdir_name in subdir_names:
                
                subdir_path = os.path.join(dir_path, subdir_name)
                names = dir_names + [subdir_name]
                
                if self._ignore_noise_dirs and subdir_name.lower() == 'noise':
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
        
        parent_dir_name = dir_names[-1].lower()
        
        try:
            station_name, start_time = self._parse_file_name(file_name)
            
        except ValueError:
            logging.error(
                'Could not parse file name "{}" at path "{}".'.format(
                    file_name, file_path))
            self._bad_file_paths.add(file_path)
        
        else:
            
            self._num_parsed_file_paths += 1
            
            try:
                _ = self._archive.get_station(station_name)
            except ValueError as e:
                self._handle_add_error(file_path, str(e))
                return
            
            self._encountered_station_names.add(station_name)
            
            sound = self._get_clip_sound(file_path)
            if sound is None:
                return
             
            detector_name = _DETECTOR_NAME
            
            clip_class_name = self._get_clip_class_name(
                station_name, detector_name, start_time, parent_dir_name)
            
            if not self._clip_class_included(clip_class_name):
                return
                
            try:
                self._archive.add_clip(
                    station_name, detector_name, start_time, sound,
                    clip_class_name)
              
            except Exception as e:
                self._handle_add_error(file_path, str(e))

            logging.info('Archived clip "{}".'.format(file_path))
            

    def _parse_file_name(self, file_name):
        base = file_name[:-len(WAVE_FILE_NAME_EXTENSION)]
        return self._parse_file_name_base(base)
        
        
    def _parse_file_name_base(self, file_name_base):
        
        parts = file_name_base.split('_')
        
        if len(parts) < 5:
            raise ValueError()
            
        num_station_name_parts = len(parts) - 4
        station_name_parts = parts[:num_station_name_parts]
        other_parts = parts[num_station_name_parts:]
        
        station_name = self._parse_station_name(station_name_parts)
        _parse_digits(other_parts[0], 1)
        start_time = _parse_start_time(other_parts[1], other_parts[2])
        _parse_digits(other_parts[3], 3)
        
        return (station_name, start_time)
        
        
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

    
    def _get_clip_class_name(
            self, station_name, detector_name, start_time, dir_name):
        
        key = (station_name, start_time)
        species_code = self._classifications.get(key)
        
        if species_code is not None:
            return 'Call.{}'.format(species_code)
        elif dir_name == 'noise':
            return 'Noise'
        else:
            return 'Call'            
 
 
    def _clip_class_included(self, clip_class_name):
        return clip_class_name.startswith(self._included_clip_classes[:-1])
         
         
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


def _parse_clip_classes_arg(keyword_args):
    
    name = 'clip-classes'
    value = vcl_utils.get_optional_keyword_arg(
        name, keyword_args, _CALL_CLIP_CLASSES)
    
    if value not in _CLIP_CLASSES_ARG_VALUES:
        options = _create_value_list(_CLIP_CLASSES_ARG_VALUES)
        raise CommandSyntaxError(
            ('Bad value "{}" for argument "--{}". Value must be '
             '{}.').format(value, name, options))
        
    return value
        
        
def _create_value_list(values):
    
    values = [('"' + v + '"') for v in values]
    
    n = len(values)
    
    if n == 1:
        return values[0]
    
    elif n == 2:
        return values[0] + ' or ' + values[1]
    
    else:
        return ', '.join(values[:-1]) + ' or ' + values[-1]
    

def _get_classifications(dir_path):
    
    """
    This is a placeholder for a function that we will write when we
    know more about the structure of the data directories that this
    importer will work with. The placeholder assumes that the KPro
    and SonoBat spreadsheet files have certain names and are located
    in the "Spreadsheets" subdirectory of the directory at `dir_path`.
    """
    
    dir_path = os.path.join(dir_path, 'Spreadsheets')
    kpro_file_path = os.path.join(dir_path, 'id.csv')
    sonobat_file_path = os.path.join(
        dir_path, 'tc_pond_5sec_split_sm2enabled-BatchClassify.txt')
    
    kpro = pd.read_csv(kpro_file_path)
    sonobat = pd.read_csv(sonobat_file_path, sep='\t')
    
    return bat_utils.merge_kpro_and_sonobat_data(kpro, sonobat)
    
    
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

