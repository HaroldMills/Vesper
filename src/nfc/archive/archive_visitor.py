"""Module containing `ArchiveVisitor` class."""


class ArchiveVisitor(object):
    
    """
    NFC clip archive visitor.
    
    The methods of a clip archive visitor are called by a clip archive walker
    as it walks the directory hierarchy of an archive.
    """
    
    def visit_year(self, info, dir_path):
        pass
    
    def visit_station(self, info, dir_path):
        pass
    
    def visit_month(self, info, dir_path):
        pass
    
    def visit_day(self, info, dir_path):
        pass
    
    def visit_clip_class(self, info, dir_path):
        pass
    
    def visit_clip(self, info, file_path):
        pass
    
    def visiting_complete(self):
        pass
