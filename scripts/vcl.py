"""
Vesper command line script.

Currently this script enables users to initialize Vesper archives and
import data into them. It will eventually include much more functionality,
enabling users to initialize, modify, and query archives.

The script is usually run indirectly, via a UNIX shell script or Windows
batch file wrapper.
"""


from __future__ import print_function

import logging
import os
import platform
import sys
import yaml

from vesper.archive.archive import Archive
from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.station import Station
from vesper.exception.command_exceptions import CommandFormatError
import vesper.util.vcl_utils as vcl_utils
import vesper.util.vesper_path_utils as vesper_path_utils


_LOG_FILE_NAME = 'vcl.log'


'''
Error handling policy:

* Command logs messages (debug, info, error, etc., but not critical) using
Python Standard Library logging module.

* Command returns boolean indicating whether or not errors occurred.
Script prints message pointing user to error log if and only if error occurs.

* Do we need to include command name in log messages? We could do this using
the `extra` keyword argument to the logging methods.
'''


'''
TODO: Investigate Ctrl-C behavior. This script should shut down gracefully
if it doesn't already, and if possible, in response to Ctrl-C.

A short script that can be interrupted by Ctrl-C:

from __future__ import print_function

import signal
import sys
import time

def signal_handler(signal, frame):
    print('You pressed Ctrl+C!')
    sys.exit(0)
    
signal.signal(signal.SIGINT, signal_handler)
print('Press Ctrl+C')
time.sleep(20)
'''


def _main():
    
    _configure_logging()
    
    if len(sys.argv) < 2:
        _usage()
        
    try:
        handler = _COMMAND_HANDLERS[sys.argv[1]]
    except KeyError:
        _usage()
        
    # TODO: Perhaps command handler should parse arguments (see below)
    positional_args, keyword_args = _parse_args(sys.argv[2:])
    
    # TODO: Handle errors better. They won't all be instances of
    # `ValueError`, for example. See commented code below for one
    # possibility.
    try:
        handler(positional_args, keyword_args)
    except ValueError as e:
        vcl_utils.log_fatal_error(str(e))
        
    # TODO: Consider executing a command in two stages, one in which
    # the command parses command line arguments and the other in which
    # the command is executed. The code might look like this:
#     try:
#         handler.configure(sys.argv[2:])
#     except CommandFormatError as e:
#         vcl_utils.log_fatal_error(str(e))
#         
#     try:
#         status = handler.execute()
#     except CommandExecutionError as e:
#         vcl_utils.log_fatal_error(str(e))
#         
#     if not status:
#         logging.info(
#             'Command completed with errors. See above messages for details.')
#         sys.exit(1)
        
      
def _configure_logging():
    
    format_ = '%(asctime)s %(levelname)-8s %(message)s'
    level = logging.INFO
    
    home_dir_path = vesper_path_utils.get_app_home_dir_path()
    log_file_path = os.path.join(home_dir_path, _LOG_FILE_NAME)
    
    # Configure output to log file.
    logging.basicConfig(
        format=format_,
        level=level,
        filename=log_file_path,
        filemode='w')
    
    # Add output to stderr.
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter(format_)
    handler.setFormatter(formatter)
    logging.getLogger('').addHandler(handler)
    
    
# TODO: Improve argument parsing, adding declarative argument
# specification, type checking, and missing and extra argument
# checks. Implement argument types and commands as extensions.
def _parse_args(args):
    
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
            
        keyword_args[name] = values
        
    return (positional_args, keyword_args)
    
    
def _usage():
    
    name = 'vcl.bat' if platform.system() == 'Windows' else 'vcl'
    
    message = '''
usage: VCL help
       VCL init <YAML file> [--archive <archive dir>]
       VCL import <importer> <source dir> [--archive <archive dir>]
       VCL detect "Old Bird" --detectors <detector names> --input-mode File --input-paths <input files/dirs> [--archive <archive dir>]
'''.strip().replace('VCL', name)

    print(message, file=sys.stderr)
    sys.exit(1)
    
    
def _init(positional_args, keyword_args):
    
    if len(positional_args) != 1:
        _usage()
        
    archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
    
    stations, detectors, clip_classes = _read_yaml_data(positional_args[0])
    
    if Archive.exists(archive_dir_path):
        vcl_utils.log_fatal_error((
            'There is already an archive at "{:s}". If you want to '
            're-initialize it to be empty, delete its contents and '
            'run this command again.').format(archive_dir_path))
        
    Archive.create(archive_dir_path, stations, detectors, clip_classes)
    
    
def _read_yaml_data(file_path):
    
    if not os.path.exists(file_path):
        vcl_utils.log_fatal_error('YAML file "{:s}" not found.'.format(file_path))
        
    data = yaml.load(open(file_path, 'r').read())
    
    station_dicts = data.get('stations', [])
    detector_names = data.get('detectors', [])
    clip_class_names = data.get('clip_classes', [])
    
    stations = [Station(**kwds) for kwds in station_dicts]
    detectors = [Detector(name) for name in detector_names]
    clip_classes = [ClipClass(name) for name in clip_class_names]
    
    return stations, detectors, clip_classes
    
    
def _import(positional_args, keyword_args):
    
    if len(positional_args) < 2:
        _usage()
        
    klass = _get_importer_class(positional_args[0])
    importer = klass()
    
    source_dir_path = positional_args[1]
    vcl_utils.check_dir_path(source_dir_path)
    
    archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
    archive = vcl_utils.open_archive(archive_dir_path)
    
    try:
        importer.import_(source_dir_path, archive)
    finally:
        archive.close()
    
    importer.log_summary()
    
    
def _get_importer_class(name):

    try:
        return _IMPORTER_CLASSES[name]
    except KeyError:
        vcl_utils.log_fatal_error('Unrecognized importer "{:s}".'.format(name))
        
        
def _detect(positional_args, keyword_args):
    
    if len(positional_args) < 1:
        _usage()
        
    klass = _get_detector_class(positional_args[0])
    
    try:
        detector = klass(positional_args[1:], keyword_args)
    except CommandFormatError as e:
        vcl_utils.log_fatal_error(str(e))
        
    detector.detect()


def _get_detector_class(name):

    try:
        return _DETECTOR_CLASSES[name]
    except KeyError:
        raise ValueError('Unrecognized detector "{:s}".'.format(name))
        
        
_COMMAND_HANDLERS = {
    'init': _init,
    'import': _import,
    'detect': _detect
}

from mpg_ranch.mpg_ranch_importer import MpgRanchImporter

_IMPORTER_CLASSES = {
    'MPG Ranch': MpgRanchImporter
}


from old_bird.detector import Detector as OldBirdDetector

_DETECTOR_CLASSES = {
    'Old Bird': OldBirdDetector
}


if __name__ == '__main__':
    _main()


'''
Vesper command line interface:

vesper help
vesper help init
  
vesper init

vesper add station Baker --description "Baker Park in downtown Ithaca, NY"
    --time-zone US/Eastern
    
vesper add detector Tseep --description "Old Bird Tseep Detector"

vesper add clip_class COYE
    --description "Common Yellowthroat, Geothlypis trichas"

vesper list stations
vesper list stations --format "name latitude longitude"
vesper list detectors
vesper list clip_classes

vesper edit station Baker --latitude 42.431985 --longitude -76.501687
vesper edit detector Tseep --name Tseep-x
vesper edit clip_class COYE --description "Common Yellowthroat"

vesper delete station Baker
vesper delete detector Tseep
vesper delete clip_class COYE

vesper import YAML <YAML file path>
vesper import "MPG Ranch" <import dir path> --start-date 2014-01-01

vesper export "Sound Files" <export dir path> --start-date ... --end-date ...
    --stations ... --detectors

vesper detect...
vesper classify...
vesper measure...

The "add" command should only be for data provided in the command itself,
and "import" for data from the file system.

What about archives in different formats?

What about remote archives, i.e. archives whose locations are not the
current directory?

Perhaps commands should all support an --archive option that specifies
an archive directory path or URL. When not specified, the current
directory is implied.
'''
    
    
'''
Vesper Python interpreter interface:

from vesper.archive import Archive

archive = Archive.create(path="/Users/Harold/Desktop/NFC/data/2015 Spring")
#archive = Archive(path="/Users/Harold/Desktop/NFC/data/2015 Spring")

archive.open()

archive.add_station(
    name="Baker", description="Baker Park in downtown Ithaca, NY",
    time_zone="US/Eastern")
archive.add_station(
    name="Flood", description="MPG Ranch Flood", time_zone="US/Mountain")
archive.add_station(
    name="Ridge", description="MPG Ranch Ridge", time_zone="US/Mountain")

archive.add_detector(name="Tseep", description="Old Bird Tseep Detector")
archive.add_detector(name="Thrush" description="Old Bird Thrush Detector")

archive.add_clip_class(name="Noise", description="non-NFC")
archive.add_clip_class(
    name="Call.Weak"
    description="call that could not be identified because it was weak")
archive.add_clip_class(name="Call.Unknown", description="unknown call")
archive.add_clip_class(
    name="COYE", description="Common Yellowthroat, Geothlypis trichas")

station = archive.get_station(name="Baker")
station.latitude = 42.431985
station.longitude = -76.501687

archive.delete_station(name="Baker")

archive.close()
'''
