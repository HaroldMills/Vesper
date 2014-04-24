"""Module containing `PrintingArchiveVisitor` class."""


from __future__ import print_function
from nfc.archive.archive_visitor import ArchiveVisitor


class PrintingArchiveVisitor(ArchiveVisitor):
    
    """
    Printing NFC clip archive visitor.
    
    This visitor prints messages that show the structure of a clip archive.
    """
    
    def visit_year(self, info, dir_path):
        pass
    
    def visit_station(self, info, dir_path):
        print('{:s} {:s}'.format(info.stationName, dir_path))
        
    def visit_month(self, info, dir_path):
        print('    {:d} {:s}'.format(info.month, dir_path))
        
    def visit_day(self, info, dir_path):
        print('        {:d} {:d} {:d} {:s}'.format(
                  info.year, info.month, info.day, dir_path))
        
    def visit_clip_class(self, info, dir_path):
        pass
#        print('            {:s}'.format(str(info.clip_class_name_components)))
        
    def visit_clip(self, info, file_path):
        pass
