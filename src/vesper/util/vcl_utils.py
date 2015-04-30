import logging
import os
import sys

from vesper.archive.archive import Archive
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
    

def create_archive(dir_path):
    
    if Archive.exists(dir_path):
        log_fatal_error((
            'Archive "{:s}" already exists. If you want to overwrite it, '
            'please delete its contents and try again.').format(dir_path))
        
    return Archive.create(dir_path)


def open_archive(dir_path):
    
    if not os.path.exists(dir_path):
        log_fatal_error(
            'Archive directory "{:s}" does not exist.'.format(dir_path))
        
    elif not os.path.isdir(dir_path):
        log_fatal_error(
            'Path "{:s}" exists but is not a directory.'.format(dir_path))
        
    elif not Archive.exists(dir_path):
        log_fatal_error((
            'Directory "{:s}" does not appear to contain an '
            'archive.').format(dir_path))
        
    archive = Archive(dir_path)
    archive.open()
    
    return archive


def check_dir_path(path):
        
    try:
        os_utils.assert_directory(path)
    except AssertionError as e:
        log_fatal_error(str(e))
        
    return path
