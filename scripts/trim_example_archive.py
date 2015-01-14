"""
Script that trims the example archive.

This script deletes from an archive the stations and detectors for which
there are no clips. It deletes noise clips if needed to reduce the fraction
of noise clips in the archive to a specified value.

The script currently assumes that archive metadata are stored in an
SQLite database with a certain structure. The archive interface should
eventually be enhanced, however, so that everything this script does
can be done through that interface. At that point the script can be
modified to be independent of archive implementation.
"""

from __future__ import print_function

import os
import random

from vesper.archive.archive import Archive


_ARCHIVE_DIR_PATH = '/Users/Harold/Desktop/NFC/Data/Old Bird/Example'
_NOISE_FRACTION = .5


class ArchiveTrimmer(object):
    
    
    def __init__(self):
        
        archive = Archive(_ARCHIVE_DIR_PATH)
        archive.open(True)
        
        self.stations = archive.stations
        self.detectors = archive.detectors
        self.clip_classes = archive.clip_classes
        
        self.conn = archive._conn
        self.cursor = archive._cursor
        
        self.archive = archive
        
        
    def trim(self):
        
        try:
            
            self._delete_extra_stations_and_detectors()
            self._delete_unwanted_clip_classes()
            self._adjust_call_to_noise_ratio()
            
            self.conn.commit()
            
        finally:
            self.archive.close()
            
        
    def _delete_extra_stations_and_detectors(self):
        
        station_counts = self._get_clip_counts(self.stations, 'station_name')
        detector_counts = self._get_clip_counts(
            self.detectors, 'detector_name')
        clip_class_counts = self._get_clip_counts(
            self.clip_classes, 'clip_class_name', ['Call*', 'Unclassified'])
            
        _show_clip_counts(station_counts, 'station')
        _show_clip_counts(detector_counts, 'detector')
        _show_clip_counts(clip_class_counts, 'clip class')
        
        self._delete_zero_count_entities(station_counts, 'station')
        self._delete_zero_count_entities(detector_counts, 'detector')
                    
        
    def _get_clip_counts(self, items, arg_name, extra_item_names=None):
        names = [i.name for i in items]
        names += extra_item_names if extra_item_names is not None else []
        return dict((n, self._get_clip_counts_aux(n, arg_name)) for n in names)
    
    
    def _get_clip_counts_aux(self, name, arg_name):
        counts = self.archive.get_clip_counts(**{arg_name: name})
        return sum(c for c in counts.itervalues())


    def _delete_zero_count_entities(self, counts, description):
        
        sql = 'delete from {:s} where name = ?'.format(description)
        
        names = [name for name, count in counts.iteritems() if count == 0]
        
        for name in names:
            
            print('deleting {:s} "{:s}"...'.format(description, name))
            
            try:
                self.cursor.execute(sql, (name,))
                
            except Exception as e:
                f = ('Could not delete {:s} "{:s}" from archive. '
                     'SQLite error message was: {:s}')
                raise ValueError(f.format(description, name, str(e)))
            
    
    def _delete_unwanted_clip_classes(self):
        
        self._delete_clips_of_class('Tone')
        self._delete_clip_class('Tone')
        self._delete_clip_class_name_component('Tone')
        
        self._delete_clips_of_class('Unclassified')
        
        
    def _delete_clips_of_class(self, clip_class_name):
        
        print('deleting {:s} clips'.format(clip_class_name))
        
        for station in self.stations:
            
            for detector in self.detectors:
                
                counts = self.archive.get_clip_counts(
                    station.name, detector.name,
                    clip_class_name=clip_class_name)
                
                nights = counts.keys()
                nights.sort()
                
                for night in nights:
                    
                    clips = self.archive.get_clips(
                        station.name, detector.name, night, clip_class_name)
                    
                    num_deleted = 0
                    
                    for clip in clips:
                        self._delete_clip(clip)
                        num_deleted += 1
                            
            
    def _delete_clip_class(self, clip_class_name):
        
        sql = 'delete from ClipClass where name = ?'
          
        try:
            self.cursor.execute(sql, (clip_class_name,))
             
        except Exception as e:
            f = ('Could not delete clip class "{:s}" from archive. '
                 'SQLite delete failed with message: {:s}')
            raise ValueError(f.format(clip_class_name, str(e)))
        
        
    def _delete_clip_class_name_component(self, name_component):
        
        sql = 'delete from ClipClassNameComponent where component = ?'
          
        try:
            self.cursor.execute(sql, (name_component,))
             
        except Exception as e:
            f = ('Could not delete clip class name component "{:s}" '
                 'from archive. SQLite delete failed with message: {:s}')
            raise ValueError(f.format(name_component, str(e)))
        
        
    def _adjust_call_to_noise_ratio(self):
        
        retention_probability = self._get_noise_retention_probability()
        
        if retention_probability < .98:
            self._delete_noises(retention_probability)
            
            
    def _get_noise_retention_probability(self):
        
        clip_class_counts = self._get_clip_counts(
            [], 'clip_class_name', ['Call*', 'Noise*'])
    
        num_calls = clip_class_counts['Call*']
        num_noises = clip_class_counts['Noise*']
        
        desired_num_noises = _NOISE_FRACTION * num_calls
        
        return min(desired_num_noises / float(num_noises), 1.)
            
    
    def _delete_noises(self, retention_probability):
        
        for station in self.stations:
            
            for detector in self.detectors:
                
                counts = self.archive.get_clip_counts(
                    station.name, detector.name, clip_class_name='Noise*')
                
                nights = counts.keys()
                nights.sort()
                
                for night in nights:
                    
                    clips = self.archive.get_clips(
                        station.name, detector.name, night, 'Noise*')
                    
                    num_deleted = 0
                    
                    for clip in clips:
                        r = random.uniform(0, 1)
                        if r > retention_probability:
                            self._delete_clip(clip)
                            num_deleted += 1
                            
                    print(station.name, detector.name, night, len(clips),
                          num_deleted)
        
    
    def _delete_clip(self, clip):
        
        sql = 'delete from Clip where id = ?'
          
        try:
            self.cursor.execute(sql, (clip._id,))
            
        except Exception as e:
            f = ('Could not delete clip with id {:d} from archive. '
                 'SQLite delete failed with message: {:s}')
            raise ValueError(f.format(clip._id, str(e)))
        
        try:
            os.remove(clip.file_path)
            
        except Exception as e:
            f = ('Could not delete clip with id {:d} from archive. '
                 'File deletion failed with message: {:s}')
            raise ValueError(f.format(clip._id, str(e)))
    
    
def _show_clip_counts(counts, item_type):
    
    print('Clip counts by {:s}:'.format(item_type))
    
    names = counts.keys()
    names.sort()
    
    for name in names:
        print('    {:s} {:d}'.format(name, counts[name]))
        
    print()


if __name__ == '__main__':
    ArchiveTrimmer().trim()
