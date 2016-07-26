"""Module containing `Recording` class."""


import datetime


class Recording(object):
    

    def __init__(self, station, num_channels, length, sample_rate, start_time):
        super(Recording, self).__init__()
        self.station = station
        self.num_channels = num_channels
        self.length = length
        self.sample_rate = float(sample_rate)
        self.start_time = start_time
        
        
    @property
    def end_time(self):
        if self.length == 0:
            return None
        else:
            return self.start_time + self.span
    
    
    @property
    def duration(self):
        
        # The *duration* of a recording is defined to be its length in
        # sample frames times its sample period.
        
        return datetime.timedelta(seconds=self.length / self.sample_rate)
    
    
    @property
    def span(self):
        
        # The *span* of a recording is the time elapsed between its first
        # and last samples, or `None` if the recording has no samples. For
        # a recording with at least one sample, the span of the recording
        # is one sample period less than its duration.
        
        length = self.length
        if length == 0:
            return None
        else:
            return datetime.timedelta(seconds=(length - 1) / self.sample_rate)
