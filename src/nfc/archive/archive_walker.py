"""Module containing `ClipArchiveWalker` class."""


from __future__ import print_function

import os

from nfc.archive.archive_parser import ArchiveParser
from nfc.util.audio_file_utils import (
    WAVE_FILE_NAME_EXTENSION as _CLIP_FILE_NAME_EXTENSION)


# TODO: Modify this class so that order of directories above the
# clip directory level is parameterized by a sequence of directory
# type names provided by the parser. For the Old Bird 2012 data
# this would be `('archive', 'station', 'month', 'day')`. I'm thinking
# that a better idea might be
# `('archive', 'station', 'year', 'month', 'day')`. The sequence of
# directory type names should drive the walk, including the names of
# the parser methods invoked to parse directory names (i.e. the method
# names should be derived from the directory type names). Information
# gathered from the directory name parses is collected in a `Bunch`
# object that can be used to process clips.
#
# This modification will both simplify the code below and make it
# more flexible.


# TODO: Perhaps we should just count clip files only in clip directories?
_CLIP_COUNTING_ENABLED = {
    'year': False,
    'station': False,
    'month': False,
    'day': True,
    'clip class': True
}


class ArchiveWalker(object):
    
    """
    NFC clip archive walker.
    
    An NFC clip archive walker walks the directory hierarchy of an
    archive, validating directory and file names and calling visitors
    along the way. The directories and files of the archive are
    visited in depth-first order.
    """
    
    
    def __init__(self, parser=None):
        
        self._parser = parser if parser is not None else ArchiveParser()
        
        self.num_accepted_files = 0
        self.num_ignored_files = 0
        
        self._visitors = set()
        
        
    def add_visitor(self, visitor):
        self._visitors.add(visitor)
        
        
    def remove_visitor(self, visitor):
        self._visitors.remove(visitor)
        
        
    def walk_archive(self, dir_path):
        (dir_path, subdir_name) = os.path.split(dir_path)
        self._walk_subdir(dir_path, subdir_name, 'year')

            
    def _walk_subdir(self, dir_path, subdir_name, subdir_type):
        
        s = subdir_type.capitalize()
        parse_method_name = 'parse{:s}DirName'.format(s)
        visit_method_name = 'visit{:s}'.format(s)
        walk_method_name = '_walk{:s}Directory'.format(s)
        
        try:
            info = getattr(self._parser, parse_method_name)(subdir_name)
            
        except ValueError, e:
            self._handle_parse_error(
                subdir_name, dir_path, subdir_type, str(e))
        
        else:
            # station parse succeeded
            
            subdir_path = os.path.join(dir_path, subdir_name)
            
            for visitor in self._visitors:
                getattr(visitor, visit_method_name)(info, subdir_path)
                
            getattr(self, walk_method_name)(subdir_path)
            
            
    def _handle_parse_error(self, subdir_name, dir_path, dir_type, message):
        
        message = (
            'Parse of {:s} directory name "{:s}" at "{:s}" failed with '
            'message: {:s}').format(dir_type, subdir_name, dir_path, message)
                   
        if _CLIP_COUNTING_ENABLED[dir_type]:
            
            subdir_path = os.path.join(dir_path, subdir_name)
            n = _count_file_names(subdir_path)
            
            suffix = '' if n == 1 else 's'
            message += (
                ' {:d} clip file{:s} in this directory will be '
                'ignored.').format(n, suffix)
        
            self.num_ignored_files += n
            
        self._handle_error(message)
        

    def _handle_error(self, message):
        if not self._suppress_message(message):
            print(message)
        
        
    def _suppress_message(self, message):
        return message.find('Could not get monitoring start time') != -1
    
    
    def _walk_year_dir(self, path):
        self._walk_dir(path, 'station')
        
        
    def _walk_dir(self, dir_path, subdir_type):
        
        for (_, subdir_names, _) in os.walk(dir_path):
            
            for subdir_name in subdir_names:
                
                self._walk_subdir(dir_path, subdir_name, subdir_type)
                
            # stop walk from visiting subdirectories
            del subdir_names[:]
        
        
    def _walk_station_dir(self, path):
        self._walk_dir(path, 'month')
        
        
    def _walk_month_dir(self, path):
        self._walk_dir(path, 'day')
        
        
    def _walk_day_dir(self, path):
        self._walk_clip_dir(path, ())
        
        
    def _walk_clip_dir(self, dir_path, clip_class_dir_names):
        
        for (_, subdir_names, file_names) in os.walk(dir_path):
            
            self._walk_clip_files(file_names, dir_path, clip_class_dir_names)
            
            self._walk_clip_subdirs(
                subdir_names, dir_path, clip_class_dir_names)
            
            # stop walk from visiting subdirectories
            del subdir_names[:]
                   
                   
    def _walk_clip_files(self, file_names, dir_path, clip_class_dir_names):
            
        info = self._parser.parse_clip_class_dir_names(clip_class_dir_names)
        
        for file_name in file_names:
            
            if file_name.endswith(_CLIP_FILE_NAME_EXTENSION):
                
                try:
                    info = self._parser.parse_clip_file_name(
                               file_name, info.clip_class_name)
                    
                except ValueError, e:
                    self._handle_file_name_parse_error(
                        file_name, dir_path, str(e))
                    
                else:
                    # parsed file name
                    
                    filePath = os.path.join(dir_path, file_name)
                    for visitor in self._visitors:
                        visitor.visit_clip(info, filePath)
                        
                    self.num_accepted_files += 1
                        
                        
    def _handle_file_name_parse_error(self, file_name, dir_path, message):
        
        message = (
            'Parse of clip file name "{:s}" at "{:s}" failed with message: '
            '{:s} File will be ignored.').format(file_name, dir_path, message)
                   
        self._handle_error(message)
        
        self.num_ignored_files += 1
                   
        
    def _walk_clip_subdirs(self, subdir_names, dir_path, clip_class_dir_names):
                
        for subdir_name in subdir_names:
            
            try:
                info = self._parser.parse_clip_class_dir_name(
                           subdir_name, clip_class_dir_names)
                
            except ValueError, e:
                self._handle_parse_error(
                    subdir_name, dir_path, 'clip class', str(e))
                
            else:
                # recognized class directory name
                
                path = os.path.join(dir_path, subdir_name)
                
                for visitor in self._visitors:
                    visitor.visit_clip_class(info, path)
                    
                self._walk_clip_dir(path, info.clip_class_dir_names)
                        
                     
def _count_file_names(arg):
    
    count = 0
    
    if isinstance(arg, list):
        # `arg` is a list of file names
        
        for file_name in arg:
            if file_name.endswith(_CLIP_FILE_NAME_EXTENSION):
                count += 1
                
    else:
        # `arg` is a directory path
        
        for (_, _, file_names) in os.walk(arg):
            count += _count_file_names(file_names)
            
    return count
