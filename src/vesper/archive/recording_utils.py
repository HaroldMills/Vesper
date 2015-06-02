"""Utility functions pertaining to recordings."""


from vesper.archive.recording import Recording


class SampleRateMismatchError(Exception):
    
    def __init__(self, recording_0, recording_1):
        super(SampleRateMismatchError, self).__init__()
        self.recording_0 = recording_0
        self.recording_1 = recording_1
        
        
def merge_recordings(recordings, tolerance=1):
    
    """
    Merges a sequence of recordings.
    
    This method partitions a sequence of recordings into subsequences of
    consecutive recordings and merges each subsequence into a single
    recording. Two recordings are deemed consecutive if the end time
    of the first recording as computed from its start time, length,
    and sample rate is not farther than `tolerance` seconds from
    the start time of the second recording.
    """
    
    
    merged_recordings = []
    
    if len(recordings) > 0:
        
        recordings.sort(key=lambda r: r.start_time)
        
        r = recordings[0]
        station = r.station
        start_time = r.start_time
        end_time = start_time + r.duration
        length = r.length
        sample_rate = r.sample_rate
        
        for r in recordings[1:]:
            
            if r.sample_rate != sample_rate:
                raise SampleRateMismatchError(recordings[0], r)
            
            delta = abs((r.start_time - end_time).total_seconds())
            
            if delta <= tolerance:
                # recording should be merged
                
                end_time = r.start_time + r.duration
                length += r.length
                
            else:
                # recording should not be merged
                
                merged_recordings.append(
                    Recording(station, start_time, length, sample_rate))
                
                start_time = r.start_time
                end_time = start_time + r.duration
                
        merged_recordings.append(
            Recording(station, start_time, length, sample_rate))
        
    return merged_recordings
