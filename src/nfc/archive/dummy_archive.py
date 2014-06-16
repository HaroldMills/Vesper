from nfc.archive.station import Station


class DummyArchive(object):
    
    
    @staticmethod
    def create(dir_path, stations, detectors, clip_classes):
        return DummyArchive(stations, detectors, clip_classes)
    
    
    def __init__(self, stations, detectors, clip_classes):
        self.stations = [Station(s.name, s.long_name, s.time_zone_name)
                         for s in stations]
        self.detectors = detectors
        self.clip_classes = clip_classes
        
        
    def get_stations(self):
        return self.stations
    
    
    def get_detectors(self):
        return self.detectors
    
    
    def get_clip_classes(self):
        return self.clip_classes
