"""Utility functions pertaining to recordings."""


from vesper.archive.recording import Recording


def merge_recordings(recordings, tolerance=1):
    
    """
    Merges a collection of recordings.
    
    This method first sorts a collection of recordings by station name
    and start time. It then merges longest subsequences of consecutive
    recordings into single recordings.
    
    Two recordings are deemed consecutive if:
    
        1. They have the same station name.
        
        2. They have the same sample rate.
    
        3. The end time of the first recording as computed from its start
           time, length, and sample rate is not farther than `tolerance`
           seconds from the start time of the second recording.
           
    Each output recording contains the input recordings that were merged
    to create it in its `subrecordings` attribute.
    """
    
    return _Merger().merge_recordings(recordings, tolerance)


class _Merger(object):
    
    
    def merge_recordings(self, recordings, tolerance):
        
        self._tolerance = tolerance
        
        merged_recordings = []
        
        if len(recordings) > 0:
            
            recordings = list(recordings)
            recordings.sort(key=lambda r: (r.station.name, r.start_time))
        
            self._start_merged_recording(recordings[0])
            
            for r in recordings[1:]:
                
                if self._is_consecutive_recording(r):
                    # recording is consecutive with last
                    
                    self._merge_recording(r)
                    
                else:
                    # recording is not consecutive with last
                    
                    merged_recording = self._end_merged_recording()
                    merged_recordings.append(merged_recording)
                    self._start_merged_recording(r)
                    
            merged_recording = self._end_merged_recording()
            merged_recordings.append(merged_recording)
            
        return merged_recordings


    def _start_merged_recording(self, r):
        self._subrecordings = [r]
        self._station = r.station
        self._start_time = r.start_time
        self._end_time = self._start_time + r.duration
        self._length = r.length
        self._sample_rate = r.sample_rate
        
        
    def _is_consecutive_recording(self, r):
        delta = abs((r.start_time - self._end_time).total_seconds())
        return r.station.name == self._station.name and \
               r.sample_rate == self._sample_rate and \
               delta <= self._tolerance


    def _merge_recording(self, r):
        self._subrecordings.append(r)
        self._end_time = r.start_time + r.duration
        self._length += r.length


    def _end_merged_recording(self):
        recording = Recording(
            self._station, self._start_time, self._length, self._sample_rate)
        recording.subrecordings = self._subrecordings
        return recording
