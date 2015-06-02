"""Module containing `Recording` class."""


import datetime


class Recording(object):
    
    """
    Sound recording.
    
    We currently store the metadata of a recording in an archive, but not
    its samples. We also support only single-channel recordings.
    """
    
    
    def __init__(self, station, start_time, length, sample_rate):
        super(Recording, self).__init__()
        self._station = station
        self._start_time = start_time
        self._length = length
        self._sample_rate = float(sample_rate)
        
        
    @property
    def station(self):
        return self._station
    
    
    @property
    def start_time(self):
        return self._start_time
    
    
    @property
    def end_time(self):
        return self.start_time + datetime.timedelta(seconds=self.duration)
    
    
    @property
    def length(self):
        return self._length
    
    
    @property
    def duration(self):
        
        # I can think of two reasonable ways to implement this method.
        # For one, we define the duration of a signal to be the time
        # interval spanned by its samples. For this definition the body
        # of this method would be:
        #
        #     n = self.length
        #     if n == 0:
        #         return 0
        #     else:
        #         return (n - 1) / self.sample_rate
        #
        # (The method might alternatively return `None` for a recording
        # of length zero.)
        #
        # Alternatively, if we define the duration of a signal to be
        # its length times its sample period. For this definition the
        # body of this method is as below.
        #
        # I can see advantages to both definitions. The first one seems
        # more natural to me from a signal processing point of view, but
        # the second one is simpler. It results in simpler code, and
        # unlike the first one it yields a mapping from length to
        # duration that is invertible.
        #
        # I chose to implement the second option for its simplicity.
        #
        # TODO: Implement the first option as a `span` method?
        
        return datetime.timedelta(seconds=self.length / self.sample_rate)


    @property
    def sample_rate(self):
        return self._sample_rate
