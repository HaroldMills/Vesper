"""
Vesper command line script.

Currently this script enables users to initialize Vesper archives and
import data into them. It will eventually include much more functionality,
enabling users to initialize, modify, and query archives.

The script is usually run indirectly, via a UNIX shell script or Windows
batch file wrapper.
"""


import logging
import os
import sys

from vesper.vcl.command import CommandSyntaxError, CommandExecutionError
import vesper.vcl.vcl_utils as vcl_utils
import vesper.util.extension_manager as extension_manager
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


'''
Query options:
    --stations <stations>
    --station <station>
    --detectors <detectors>
    --detector <detector>
    --clip-classes <clip classes>
    --clip-class <clip class>
    --date <date>
    --start-date <start date>
    --end-date <end date>

vcl classify clip --id 789378937893 --clip-class Noise
vcl classify clips --station Alfred --detector Tseep --date 2014-06-01
    --clip-class Noise
vcl classify clips --classifier "MPG Ranch Diurnal Classifier"
vcl classify "MPG Ranch Diurnal Classifier"
    <query options>

vcl export clips --data "MPG Ranch Clip Stats 1.00" --format CSV
vcl export "MPG Ranch Clips CSV"
    --output-file <file path> <query options>
    
vcl export clips --data "Sound" --format WAV
vcl export clips --export-format "Sound Files" --time-zone "US/Eastern"
vcl export "Sound Files" --time-zone "US/Eastern"
    <query options>
    
vcl list clips --limit 10

vcl update clip-class --with-name AMRE
'''


def _main():
    
    _configure_logging()
    
    n = len(sys.argv)
    if n < 2:
        _usage('No command specified.')
        
    command_classes = extension_manager.get_extensions('VCL Command')
    command_name = sys.argv[1]
    
    try:
        command_class = command_classes[command_name]
    except KeyError:
        _usage('Unrecognized command "{:s}".'.format(command_name))
        
    # TODO: Perhaps command handler should parse arguments (see below)
    positional_args, keyword_args = \
        vcl_utils.parse_command_line_args(sys.argv[2:])
    
    try:
        command = command_class(positional_args, keyword_args)
    except CommandSyntaxError as e:
        vcl_utils.log_fatal_error('Command syntax error: {:s}'.format(str(e)))
        
    try:
        success = command.execute()
    except CommandExecutionError as e:
        vcl_utils.log_fatal_error(
            'Command "{:s}" failed with fatal error: {:s}'.format(
                command.name, str(e)))
        
    if success:
        suffix = 'no errors.'
    else:
        suffix = 'one or more non-fatal errors. See log for details.'
        
    logging.info(
        'Command "{:s}" completed with {:s}'.format(command.name, suffix))
    
    sys.exit(0 if success else 1)
        
      
def _configure_logging():
    
    format_ = '%(asctime)s %(levelname)-8s %(message)s'
    level = logging.INFO
    
    app_data_dir_path = vesper_path_utils.get_path('App Data')
    log_file_path = os.path.join(app_data_dir_path, _LOG_FILE_NAME)
    
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
    
    
def _usage(message):
    
    command_classes = extension_manager.get_extensions('VCL Command')
    
    try:
        command_class = command_classes['help']
        
    except KeyError:
        
        text = '''
Usage: vcl <command> [<positional arguments>] [<keyword arguments>]
    
Available commands:
'''.strip()
    
        command_names = sorted(command_classes.keys())
        command_names = '\n'.join(('    ' + n) for n in command_names)
        
        text += '\n' + command_names + '\n'
        
        print(text)
    
    else:
        command = command_class([], {})
        command.execute()

    vcl_utils.log_fatal_error(message)
        
    
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
