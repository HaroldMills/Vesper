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
import yaml

from vesper.archive.archive import Archive
from vesper.archive.clip_class import ClipClass
from vesper.archive.detector import Detector
from vesper.archive.station import Station


def _main():
    
    logging.basicConfig(format='%(message)s', level=logging.INFO)
    
    if len(sys.argv) < 2:
        _usage()
        
    try:
        handler = _COMMAND_HANDLERS[sys.argv[1]]
    except KeyError:
        _usage()
        
    handler(os.getcwd(), sys.argv[2:])
    

def _usage():
    _log_fatal_error('''
usage: vesper init <YAML file>
       vesper import <importer> <source dir>
'''.strip())
    
    
def _log_fatal_error(message):
    logging.critical(message)
    sys.exit(1)
    
    
def _init(archive_dir_path, args):
    
    if len(args) != 1:
        _usage()
        
    stations, detectors, clip_classes = _read_yaml_data(args[0])
    
    # TODO: Warn if archive already exists, and confirm that user
    # wants to overwrite it. This might be done with the help of
    # a new `Archive.exists` function.
    
    Archive.create(archive_dir_path, stations, detectors, clip_classes)
    
    
def _read_yaml_data(file_path):
    
    if not os.path.exists(file_path):
        _log_fatal_error('YAML file "{:s}" not found.'.format(file_path))
        
    data = yaml.load(open(file_path, 'r').read())
    
    station_dicts = data.get('stations', [])
    detector_names = data.get('detectors', [])
    clip_class_names = data.get('clip_classes', [])
    
    stations = [Station(**kwds) for kwds in station_dicts]
    detectors = [Detector(name) for name in detector_names]
    clip_classes = [ClipClass(name) for name in clip_class_names]
    
    return stations, detectors, clip_classes
    
    
def _add(archive_dir_path, args):
    logging.info('add "{:s}" {:s}'.format(archive_dir_path, str(args)))
    
    
def _import(archive_dir_path, args):
    
    archive = _get_archive(archive_dir_path)
    
    if len(args) < 2:
        _usage()
        
    importer_klass = _get_importer_class(args[0])
    
    source_dir_path = args[1]
    _check_dir_path(source_dir_path)
    
    importer = importer_klass()
    
    # TODO: Use `with` statement?
    archive.open()
    
    try:
        importer.import_(source_dir_path, archive)
    finally:
        archive.close()
    
    importer.log_summary()
    
    
def _get_archive(archive_dir_path):
    _check_dir_path(archive_dir_path)
    return Archive(archive_dir_path)
    
    
def _get_importer_class(name):

    try:
        return _IMPORTER_CLASSES[name]
    except KeyError:
        _log_fatal_error('Unrecognized importer "{:s}".'.format(name))
        
        
def _check_dir_path(path):
        
    if not os.path.exists(path):
        m = 'Directory "{:s}" does not exist.'
        _log_fatal_error(m.format(path))
        
    if not os.path.isdir(path):
        m = 'Path "{:s}" exists but is not a directory.'
        _log_fatal_error(m.format(path))
        
    return path
        
    
_COMMAND_HANDLERS = {
    'init': _init,
    'add': _add,
    'import': _import
}

from mpg_ranch.mpg_ranch_importer import MpgRanchImporter

_IMPORTER_CLASSES = {
    'MPG Ranch': MpgRanchImporter
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
