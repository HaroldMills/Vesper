"""Module containing `DummyArchive` class."""


class DummyArchive(object):
    
    """Trivial archive implementation for testing purposes."""
    
    
    @staticmethod
    def create(dir_path, stations, detectors, clip_classes):
        return DummyArchive(stations, detectors, clip_classes)
    
    
    def __init__(self, stations, detectors, clip_classes):
        self.stations = stations
        self.detectors = detectors
        self.clip_classes = clip_classes
        
        
    def open(self, cache_db=False):
        pass
    
    
    def close(self):
        pass
