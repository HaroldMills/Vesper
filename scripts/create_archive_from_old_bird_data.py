"""Creates a clip archive from Old Bird clip directories."""


from __future__ import print_function

import os

from nfc.archive.archive_walker import ArchiveWalker
from nfc.archive.copying_archive_visitor import CopyingArchiveVisitor
from old_bird.archive_constants import (
    CLIP_CLASSES, DETECTORS, STATIONS)
from old_bird.archive_parser import OldBirdArchiveParser


_NFC_DIR_PATH = '/Users/Harold/Desktop/NFC/Clips/Old Bird'
_FROM_PATH = os.path.join(_NFC_DIR_PATH, '2012 Summer and Fall Uncleaned')
_TO_PATH = os.path.join(_NFC_DIR_PATH, '2012 Summer and Fall')


def _main():
    
    parser = OldBirdArchiveParser()
    walker = ArchiveWalker(parser)
    
    _create_dir(_TO_PATH)
    
    visitor = CopyingArchiveVisitor(
        _TO_PATH, STATIONS, DETECTORS, CLIP_CLASSES)
    walker.add_visitor(visitor)
    
    walker.walk_archive(_FROM_PATH)
    
    visitor.visiting_complete()
    
    print('Found {:d} absolute clip file names.'.format(
              parser.num_absolute_file_names))
    print(('Found {:d} relative clip file names, of which {:d} could ',
           'not be resolved.').format(
              parser.num_relative_file_names,
              parser.num_unresolved_relative_file_names))
    print('Found {:d} bad clip file names.'.format(parser.num_bad_file_names))
    print('Ignored {:d} clip files.'.format(walker.num_ignored_files))
    print('Accepted {:d} clip files.'.format(parser.num_accepted_files))
    
    print('{:d} clip files were duplicates.'.format(
              visitor.num_duplicate_files))
    print('{:d} sound files were bad.'.format(visitor.num_bad_files))
    print('{:d} clips could not be added to the archive.'.format(
              visitor.num_add_errors))
    

def _create_dir(path):
    if not os.path.exists(path):
        os.makedirs(_TO_PATH)
        
        
if __name__ == '__main__':
    _main()
