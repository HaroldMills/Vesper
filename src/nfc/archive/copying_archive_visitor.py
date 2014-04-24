"""Module containing `CopyingArchiveVisitor` class."""


from __future__ import print_function

from nfc.archive.archive import Archive
from nfc.archive.archive_visitor import ArchiveVisitor
import nfc.util.sound_utils as sound_utils


class CopyingArchiveVisitor(ArchiveVisitor):
    
    """NFC clip archive visitor that copies clip files to a new archive."""
    
    
    def __init__(self, archive_dir_path, stations, detectors, clip_classes):
        
        self._archive = Archive.create(
            archive_dir_path, stations, detectors, clip_classes)
        
        self._clip_dir_paths = set()
        self._clip_info = {}
        
        self.num_duplicate_files = 0
        self.num_bad_files = 0
        self.num_add_errors = 0
        
        
    def visit_day(self, info, dir_path):
        print('{:s} {:d}-{:02d}-{:02d}...'.format(
                  info.station_name, info.year, info.month, info.day))
        
        
    def visit_clip(self, info, file_path):
        
        station_name = info.station_name
        detector_name = info.detector_name
        time = info.time
        key = (station_name, detector_name, time)
        
        try:
            clip = self._clip_info[key]
        
        except KeyError:
            # do not already have clip for this station, detector, and time
            
            try:
                sound = sound_utils.read_sound_file(file_path)
                
            except Exception, e:
                print('Error reading sound file "{:s}": {:s}'.format(
                          file_path, str(e)))
                self.num_bad_files += 1
            
            else:
                # successfully read sound file
                
                try:
                    clip = self._archive.add_clip(
                        station_name, detector_name, time, sound,
                        info.clip_class_name)
                    
                except Exception, e:
                    print('Error adding clip from "{:s}": {:s}'.format(
                              file_path, str(e)))
                    self.num_add_errors += 1
                    
                else:
                    self._clip_info[key] = clip
            
        else:
            # already have clip for this station, detector, and time
            
            old = clip.clip_class_name
            new = info.clip_class_name
            
            if new != old:
                
                if old is None or \
                   new is not None and \
                   new.startswith(old) and \
                   new[len(old)] == '.':
                    # new classification is same as or more specific
                    # version of old one
                
                    clip.clip_class_name = new
                    
                
                else:
                    # new classification differs from old one and is not
                    # a more specific version of it
                    
                    # TODO: Mark clips for which there were
                    # reclassifications in the database.
                    print(
                        ('Clip ("{:s}", "{:s}", {:s}) reclassified from '
                         '{:s} to {:s}.').format(
                              station_name, detector_name, str(time),
                              repr(old), repr(new)))
                
            self.num_duplicate_files += 1
        
        
    def visiting_complete(self):
        self._archive.close()
