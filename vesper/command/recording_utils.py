"""Utility functions pertaining to recordings."""


import datetime
import logging

from vesper.command.command import CommandExecutionError
from vesper.util.bunch import Bunch
import vesper.util.signal_utils as signal_utils


def create_recording_file_parser(spec):
    
    # These imports are here instead of at the top of this module so
    # they don't interfere with unit tests for other functions of the
    # module.
    from vesper.singleton.extension_manager import extension_manager
    from vesper.django.app.models import Station
    
    # Get parser name.
    classes = extension_manager.get_extensions('Recording File Parser')
    name = spec.get('name')
    if name is None:
        raise CommandExecutionError(
            'Recording file parser spec does not include parser name.')
        
    # Get parser class.
    cls = classes.get(name)
    if cls is None:
        raise CommandExecutionError(
            'Unrecognized recording file parser extension "{}".'.format(name))

    # Get stations.
    stations = [s for s in Station.objects.all()]
    
    # Get station name aliases.
    station_name_aliases = _get_station_name_aliases(spec)
    
    # Create parser.
    parser = cls(stations, station_name_aliases)
    
    return parser
    
    
def _get_station_name_aliases(spec):
    
    # This import is here instead of at the top of this module so it
    # won't interfere with unit tests for other functions of the module.
    from vesper.singleton.preset_manager import preset_manager

    args = spec.get('arguments')
    
    if args is None:
        return {}
    
    preset_name = args.get('station_name_aliases_preset')
    
    if preset_name is None:
        return {}
    
    preset_path = ('Station Name Aliases', preset_name)
    preset = preset_manager.get_preset(preset_path)
    
    if preset is None:
        logging.getLogger().warning((
            'Could not find Station Name Aliases preset "{}". '
            'No station name aliases will be recognized in recording '
            'file names during the import.').format(preset_name))
        return {}
    
    return preset.data


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
