"""Utility functions pertaining to Vesper command line program."""


import logging
import os
import re
import sys

from vesper.archive.archive import Archive
from vesper.vcl.command import CommandExecutionError, CommandSyntaxError
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils


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
    
    
def get_archive_dir_path(keyword_args):
    
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
    start_date, end_date = get_dates(keyword_args)
    return (station_names, detector_names, clip_class_names, start_date,
            end_date)
        
    
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
    
    
def get_dates(keyword_args):
    
    # TODO: Support "dates" keyword argument. It should allow the
    # specification of multiple dates and date ranges. A range is
    # specified by joining two dates with a colon, for example
    # "2015-06-01:2015-06-10".
    #
    # The dates of a query can be represented as a sequence of ranges
    # (where some ranges may contain only one date) ordered by
    # increasing start date. A simple algorithm to merge overlapping
    # and consecutive date ranges merges consecutive pairs of ranges
    # whenever possible, beginning at the top of the list and
    # advancing downward until reaching the end of the list.
    
    args = keyword_args
    
    if 'date' in args and 'start-date' in args:
        _handle_exclusivity_error('date', 'start-date')
        
    elif 'date' in args and 'end-date' in args:
        _handle_exclusivity_error('date', 'end-date')
        
    elif 'date' in args:
        date = _get_date(args, 'date')
        return (date, date)
    
    else:
        start_date = _get_date(args, 'start-date')
        end_date = _get_date(args, 'end-date')
        _check_date_order(start_date, end_date)
        return (start_date, end_date)
        
    
def _get_date(args, name):
    
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


def _check_date_order(start_date, end_date):
    
    if start_date is not None and \
            end_date is not None and \
            start_date > end_date:
        
        # TODO: This isn't really a syntax error. Should we change
        # the exception class name to `CommandParseError`?
        raise CommandSyntaxError(
            'Start date "{:s}" follows end date "{:s}".'.format(
                format_date(start_date), format_date(end_date)))
        
        
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
