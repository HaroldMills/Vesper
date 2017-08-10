"""Utility functions pertaining to recordings."""


import datetime

from vesper.util.bunch import Bunch
import vesper.util.signal_utils as signal_utils


def group_recording_files(files, tolerance=1):
    
    """
    Groups audio files into continuous recordings.
    
    This function groups audio files according to the recordings to
    which they belong. More specifically, the function first sorts the
    files by station name, recorder name, recorder channel numbers,
    number of channels, sample rate, and start time. It then inspects
    the files in order, grouping consecutive subsequences of them into
    recordings.
    
    As files are being grouped into recordings, the next file is added
    to the current recording if either the recording is empty or:
    
        1. The file has the same station, recorder, recorder channel
           numbers, number of channels, and sample rate as the recording.
    
        2. The absolute value of the difference between the start time
           of the file and the end time of the recording does not
           exceed a threshold. The threshold is the maximum of one second
           (we always allow at least this much difference since file time
           stamps are rounded to the nearest second) and the duration of
           the recording in hours times the tolerance. This compensates
           for sample clock inaccuracies and drift, both of which are
           common.
           
    If the current recording is not empty and the two conditions above
    are not satisfied for the next file, the recording is terminated and
    a new recording is started with the file.
    
    :Parameters:
    
        files : set or sequence of file `Bunch` objects
            information about the files to be grouped into recordings.
            
        tolerance : float
            the file grouping tolerance in seconds per hour.
            
    :Returns:
        a sequence of recording `Bunch` objects.
        
        Each `Bunch` object contains information regarding one recording.
        Information about the files of a recording is included in the
        `files` attribute, a sequence of `Bunch` objects, one for each
        recording file. The returned recordings are sorted by station
        name, recorder name, recorder channel numbers, number of channels,
        sample rate, and start time.
    """
    
    return _FileGrouper().group(files, tolerance)


class _FileGrouper:
    
    
    def group(self, files, tolerance):
        
        self.tolerance = tolerance
        
        recordings = []
        
        if len(files) > 0:
            
            files = list(files)
            files.sort(key=_create_sort_key)
        
            self._start_recording(files[0])
            
            for f in files[1:]:
                
                if self._is_consecutive_file(f):
                    # file is consecutive with last
                    
                    self._append_file(f)
                    
                else:
                    # recording is not consecutive with last
                    
                    recording = self._end_recording()
                    recordings.append(recording)
                    self._start_recording(f)
                    
            recording = self._end_recording()
            recordings.append(recording)
            
        return recordings


    def _start_recording(self, f):
        self.station = f.station
        self.recorder = f.recorder
        self.recorder_channel_nums = f.recorder_channel_nums
        self.mic_outputs = f.mic_outputs
        self.num_channels = f.num_channels
        self.length = f.length
        self.sample_rate = f.sample_rate
        self.start_time = f.start_time
        self.files = [f]
        
        
    def _is_consecutive_file(self, f):
        
        duration = signal_utils.get_duration(self.length, self.sample_rate)
        end_time = self.start_time + datetime.timedelta(seconds=duration)
        delta = abs((f.start_time - end_time).total_seconds())
        threshold = max(1, duration * self.tolerance / 3600)
        
        return f.station == self.station and \
            f.recorder == self.recorder and \
            f.recorder_channel_nums == self.recorder_channel_nums and \
            f.mic_outputs == self.mic_outputs and \
            f.num_channels == self.num_channels and \
            f.sample_rate == self.sample_rate and \
            delta <= threshold


    def _append_file(self, f):
        self.files.append(f)
        self.length += f.length


    def _end_recording(self):
        return Bunch(
            station=self.station,
            recorder=self.recorder,
            recorder_channel_nums=self.recorder_channel_nums,
            mic_outputs=self.mic_outputs,
            num_channels=self.num_channels,
            length=self.length,
            sample_rate=self.sample_rate,
            start_time=self.start_time,
            files=self.files)


def _create_sort_key(f):
    return (
        f.station.name, f.recorder.name, f.recorder_channel_nums,
        tuple(str(o) for o in f.mic_outputs),
        f.num_channels, f.sample_rate, f.start_time)
