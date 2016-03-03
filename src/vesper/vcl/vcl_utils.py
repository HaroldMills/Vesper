"""Utility functions pertaining to Vesper command line program."""


import logging
import os
import re
import sys
import yaml

from vesper.archive.archive import Archive
from vesper.util.bunch import Bunch
from vesper.vcl.command import CommandExecutionError, CommandSyntaxError
import vesper.util.extension_manager as extension_manager
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


def get_command_delegate_extension(
        extension_name, extension_point_name, delegate_description):
    
    extensions = extension_manager.get_extensions(extension_point_name)
    
    try:
        return extensions[extension_name]
    
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized {:s} "{:s}".'.format(
                delegate_description, extension_name))


def parse_command_args_yaml(s):
    args = yaml.load(s)
    args = _transform_args(args)
    descriptors = [Bunch(**a) for a in args]
    return descriptors


def _transform_args(args):
    return [_transform_arg(a) for a in args]


def _transform_arg(arg):
    result = dict((k.replace(' ', '_'), v) for k, v in arg.iteritems())
    result['name'] = result['name'].replace(' ', '-')
    return result
                
                
_ARCHIVE_ARGS = '''

- name: --archive
  required: false
  value description: directory path
  documentation: |
      The archive on which to operate.
      Default: The archive of current directory.
'''


ARCHIVE_ARG_DESCRIPTORS = parse_command_args_yaml(_ARCHIVE_ARGS)


_CLIP_QUERY_ARGS = '''

- name: --stations
  required: false
  value description: station names
  documentation: |
      The stations of the clips to process.
      Default: All stations.
  
- name: --detectors
  required: false
  value description: detector names
  documentation: |
      The detectors of the clips to process.
      Default: All detectors.
  
- name: --night
  required: false
  value description: YYYY-MM-DD
  documentation: |
      The night of the clips to process.
      The night is specified by the date on which it began.
      Specifying this argument is the same as specifying the --start-night
      and --end-night arguments with the same date. If this argument is
      provided, neither of those arguments should be provided.
  
- name: --start-night
  required: false
  value description: YYYY-MM-DD
  documentation: |
      The start night of the clips to process.
      The night is specified by the date on which it began.
      Default: The start night of the archive.
  
- name: --end-night
  required: false
  value description: YYYY-MM-DD
  documentation: |
      The end night of the clips to process.
      The night is specified by the date on which it began.
      Default: The end night of the archive.
  
- name: --clip-classes
  required: false
  value description: clip class names
  documentation: |
      The clip classes of the clips to process.
      Default: All clip classes.
'''


CLIP_QUERY_ARG_DESCRIPTORS = parse_command_args_yaml(_CLIP_QUERY_ARGS)


def create_command_args_help(descriptors):
    
    required_args = [d for d in descriptors if d.required]
    required_text = _create_args_help(required_args, 'Required')
    
    optional_args = [d for d in descriptors if not d.required]
    optional_text = _create_args_help(optional_args, 'Optional')
    
    return (required_text + '\n\n' + optional_text).strip()


def _create_args_help(descriptors, title_prefix):
    title = title_prefix + ' keyword arguments:'
    if len(descriptors) == 0:
        args = ['    None.']
        return title + '\n    None.'
    else:
        args = [_create_arg_help(d) for d in descriptors]
        return '\n\n'.join([title] + args)


def _create_arg_help(d):
    header = '    {:s} <{:s}>'.format(d.name, d.value_description)
    try:
        doc = d.documentation
    except AttributeError:
        doc_lines = []
    else:
        doc_lines = doc.strip().split('\n')
        doc_lines = ['        ' + line for line in doc_lines]
    return '\n'.join([header] + doc_lines)
        

# TODO: Improve argument parsing, with such things as declarative argument
# specification by command classes, type checking, and missing and extra
# argument checks. Implement argument types and commands as extensions.
def parse_command_line_args(args):
    
    i = 0
    while i != len(args) and not args[i].startswith('--'):
        i += 1
        
    positional_args = tuple(args[:i])
    
    keyword_args = {}
    
    while i != len(args):
        
        name = args[i][2:]
        i += 1
        
        values = []
        while i != len(args) and not args[i].startswith('--'):
            values.append(args[i])
            i += 1
            
        keyword_args[name] = tuple(values)
        
    return (positional_args, keyword_args)
    
    
def get_required_keyword_arg(name, keyword_args):
    values = get_required_keyword_arg_tuple(name, keyword_args)
    return _get_singleton_arg_value(values, name)


def _get_singleton_arg_value(values, name):
    _check_arg_values_count(name, values, 1, 1)
    return values[0]


def get_required_keyword_arg_tuple(name, keyword_args):
    try:
        return keyword_args[name]
    except KeyError:
        message = 'Missing required keyword argument "--{:s}".'.format(name)
        raise CommandSyntaxError(message)
    
    
def get_optional_keyword_arg(name, keyword_args, default=None):
    
    try:
        values = keyword_args[name]
    except KeyError:
        return default
    else:
        return _get_singleton_arg_value(values, name)
    
    
def get_optional_keyword_arg_tuple(name, keyword_args, default=None):
    
    if default is not None:
        if not isinstance(default, tuple):
            raise TypeError(
                ('A tuple is required as the default value for '
                 'argument "--{:s}".').format(name))
            
    try:
        values = keyword_args[name]
    except KeyError:
        return default
    else:
        return values


# def get_optional_boolean_keyword_arg(name, keyword_args, default):
#     try:
#         values = keyword_args[name]
#     except KeyError:
#         return default
#     else:
#         if len(values) == 0:
#             return default
#         else:
#             _check_arg_values_count(name, values, max_count=1)
#             return _parse_boolean_arg_value(name, values[0])
#                 
#         
# def _parse_boolean_arg_value(name, value):
#     if value == 'true':
#         return True
#     elif value == 'false':
#         return False
#     else:
#         raise TypeError(
#             ('A value of either "true" or "false" is required for '
#              'argument "--{:s}".').format(name))
    
    
def get_archive_dir_path(keyword_args):
    
    # We make a separate function for this rather than just using
    # `get_optional_keyword_arg` for two reasons:
    #
    #    1. The `archive` keyword argument is common.
    #
    #    2. We would prefer not to invoke `os.getcwd` unless we have to.
    #       If we were to use `get_optional_keyword_arg`, we would always
    #       invoke `os.getcwd` at each call site to get the default value
    #       to pass to `get_optional_keyword_arg`.

    try:
        paths = keyword_args['archive']
    except KeyError:
        return os.getcwd()
    else:
        return paths[0]
    

def get_clip_query(keyword_args):
    station_names = get_station_names(keyword_args)
    detector_names = get_detector_names(keyword_args)
    clip_class_names = get_clip_class_names(keyword_args)
    start_night, end_night = get_nights(keyword_args)
    return (station_names, detector_names, clip_class_names, start_night,
            end_night)
        
    
def get_station_names(keyword_args):
    return _get_arg_values(keyword_args, 'station', 'stations')
    
    
def _get_arg_values(args, singular_name, plural_name):
        
    if singular_name in args and plural_name in args:
        _handle_exclusivity_error(singular_name, plural_name)
        
    elif singular_name in args:
        values = args[singular_name]
        _check_arg_values_count(singular_name, values, 1, 1)
        return values
        
    elif plural_name in args:
        values = args[plural_name]
        _check_arg_values_count(plural_name, values, 1)
        return values
    
    else:
        return None
    
    
def _handle_exclusivity_error(name_a, name_b):
    raise CommandSyntaxError((
        'Both "--{:s}" and "--{:s}" arguments specified. One or the other '
        'may be specified, but not both.').format(name_a, name_b))


def _check_arg_values_count(name, values, min_count=None, max_count=None):
    
    count = len(values)
    
    if min_count is not None and count < min_count:
        phrase = _get_value_count_phrase(min_count)
        raise CommandSyntaxError((
            'Too few values for argument "--{:s}". At least '
            '{:s} required.').format(name, phrase))
        
    if max_count is not None and count > max_count:
        phrase = _get_value_count_phrase(max_count)
        raise CommandSyntaxError((
            'Too many values for argument "--{:s}". At most '
            '{:s} allowed.').format(name, phrase))
        
        
def _get_value_count_phrase(count):
    if count == 1:
        return 'one value is'
    else:
        return '{:d} values are'.format(count)

    
def get_detector_names(keyword_args):
    return _get_arg_values(keyword_args, 'detector', 'detectors')
    
    
def get_clip_class_names(keyword_args):
    return _get_arg_values(keyword_args, 'clip-class', 'clip-classes')
    
    
def get_nights(keyword_args):
    
    args = keyword_args
    
    if 'night' in args and 'start-night' in args:
        _handle_exclusivity_error('night', 'start-night')
        
    elif 'night' in args and 'end-night' in args:
        _handle_exclusivity_error('night', 'end-night')
        
    elif 'night' in args:
        night = _get_night(args, 'night')
        return (night, night)
    
    else:
        start_night = _get_night(args, 'start-night')
        end_night = _get_night(args, 'end-night')
        _check_night_order(start_night, end_night)
        return (start_night, end_night)
        
    
def _get_night(args, name):
    
    try:
        values = args[name]
        
    except KeyError:
        return None
    
    else:
        
        _check_arg_values_count(name, values, 1, 1)
        
        value = values[0]
        
        try:
            return parse_date(value)
        
        except CommandSyntaxError:
            raise CommandSyntaxError(
                'Bad date value "{:s}" for argument "--{:s}".'.format(
                    value, name))


_DATE_RE = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)$')


def parse_date(date):
    
    m = _DATE_RE.match(date)
     
    if m is None:
        _handle_bad_date(date)
     
    try:
        return time_utils.parse_date(*m.groups())
    except ValueError:
        _handle_bad_date(date)
    
    
def _handle_bad_date(value):
    raise CommandSyntaxError('Bad date "{:s}"'.format(value))


def _check_night_order(start_night, end_night):
    
    if start_night is not None and \
            end_night is not None and \
            start_night > end_night:
        
        # TODO: This isn't really a syntax error. Should we change
        # the exception class name to `CommandParseError`?
        raise CommandSyntaxError(
            'Start night "{:s}" follows end night "{:s}".'.format(
                format_date(start_night), format_date(end_night)))
        
        
def format_date(date):
    return date.strftime('%Y-%m-%d')


def log_fatal_error(message):
    logging.critical(message)
    sys.exit(1)
    
    
def create_archive(dir_path, stations=None, detectors=None, clip_classes=None):
    
    if Archive.exists(dir_path):
        raise CommandExecutionError((
            'There is already an archive at "{:s}". If you want to '
            'create a new archive at this location, you must first '
            'delete the existing one.').format(dir_path))
        
    try:
        return Archive.create(dir_path, stations, detectors, clip_classes)
    except Exception as e:
        raise CommandExecutionError((
            'Archive creation raised {:s} exception with message: '
            '{:s}').format(e.__class__.__name__, str(e)))


def open_archive(dir_path):
    
    if not os.path.exists(dir_path):
        raise CommandExecutionError(
            'Archive directory "{:s}" does not exist.'.format(dir_path))
        
    elif not os.path.isdir(dir_path):
        raise CommandExecutionError(
            'Path "{:s}" exists but is not a directory.'.format(dir_path))
        
    elif not Archive.exists(dir_path):
        raise CommandExecutionError((
            'Directory "{:s}" does not appear to contain an '
            'archive.').format(dir_path))
        
    try:
        archive = Archive(dir_path)
        archive.open()
    except Exception as e:
        raise CommandExecutionError(
            'Archive open raised {:s} exception with message: {:s}'.format(
                e.__class__.__name__, str(e)))
        
    return archive


def check_dir_path(path):
        
    try:
        os_utils.assert_directory(path)
    except AssertionError as e:
        raise CommandExecutionError(str(e))
        
    return path
