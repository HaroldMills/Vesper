"""Module containing class `SampleProvider`."""


class SampleProvider:
    
    """
    Signal sample provider.
    
    A `SampleProvider` is an auxiliary object that helps signal
    indexers get signal samples. 
    """
    
    
    def __init__(self, frame_first):
        self._frame_first = frame_first
        
        
    @property
    def frame_first(self):
        return self._frame_first
        
        
    def get_samples(self, first_key, second_key):
        
        # `first_key` and `second_key` can be either integers or slices.
        # If a `SampleProvider` is frame-first, the first key is the
        # frame number and the second key is the channel number. If
        # a `SampleProvider` is channel-first, that order is reversed:
        # the first key is the channel number and the second key is
        # the frame number.
 
        raise NotImplementedError()
