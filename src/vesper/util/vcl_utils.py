import logging
import os
import sys

from vesper.archive.archive import Archive
from vesper.vcl.command import CommandExecutionError
import vesper.util.os_utils as os_utils


def log_fatal_error(message):
    logging.critical(message)
    sys.exit(1)
    
    
def get_archive_dir_path(keyword_args):
    
    try:
        paths = keyword_args['archive']
    except KeyError:
        return os.getcwd()
    else:
        return paths[0]
    

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
