"""Module containing class `ReadDelegate`."""


class SampleReadDelegate:
    
    """
    Read delegate for signal sample readers.
    
    A `SampleReadDelegate` is an auxiliary signal object to which the
    signal's readers delegate sample reads.
    """
    
    
    def __init__(self, frame_first):
        self._frame_first = frame_first
        
        
    @property
    def frame_first(self):
        return self._frame_first
        
        
    def read(self, first_key, second_key):
        
        # `first_key` and `second_key` can be either integers or slices.
        # If a `SampleReadDelegate` is frame-first, the first key is the
        # frame number and the second key is the channel number. If a
        # `SampleReadDelegate` is channel-first, that order is reversed:
        # the first key is the channel number and the second key is
        # the frame number.
 
        raise NotImplementedError()
