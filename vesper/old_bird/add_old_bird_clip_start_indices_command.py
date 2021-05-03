"""Module containing class `AddOldBirdClipStartIndicesCommand`."""


from collections import defaultdict
import datetime
import itertools
import logging
import time

from django.db import transaction
import numpy as np

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Clip, Processor, Recording, Station
from vesper.old_bird.recording_reader import RecordingReader
from vesper.singleton.archive import archive
from vesper.singleton.clip_manager import clip_manager
from vesper.singleton.recording_manager import recording_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.signal_utils as signal_utils
import vesper.util.text_utils as text_utils


_INITIAL_CLIP_SEARCH_PADDING = 5
_FINAL_CLIP_SEARCH_PADDING = 5
"""
Padding for recording clip search, in seconds.

Since the Old Bird detectors only provide an approximate start time
of a clip in a recording (as an integer number of seconds from the
start of the recording), to find the exact index of a clip in a
recording we must search for the clip in the recording. We do this
by searching for the clip in the portion of the recording that starts
`_INITIAL_CLIP_SEARCH_PADDING` seconds before the approximate clip
start time and ends `_FINAL_CLIP_SEARCH_PADDING` seconds after the
approximate end time.

We calculate the start index of the portion of a recording in which
to search for clip samples using the purported sample rate of the
recording. Because the actual sample rate of a recording often
differs from the purported sample rate by a small amount, the
calculated start index may be inaccurate, and the inaccuracy grows
the further into a recording a clip is located. For this reason we
use a larger padding than would otherwise be necessary. We have
processed some recordings (made at the MPG Ranch Darby station in
2016) for which a padding of two seconds was insufficient, so that
clips could not be located beginning roughly six hours into the
recordings. The maximum recording duration was about 12 hours,
so we increased the padding to five seconds, which allowed us to
find all of the clips. The additional padding slowed processing
by about 20 percent.

Another, more sophisticated approach to this problem would be to
compare the start indices of clips we find to their purported
start times to estimate the actual sample rate of a recording,
and use that estimate to revise the start time of a clip before
searching for its samples. That would take extra work, however,
and the current approach has worked alright so far.
"""

_CLIP_SEARCH_TOLERANCE = 1
"""
Search tolerance for sample value differences.

The samples saved by the Old Bird detectors to a clip audio file
can differ from the corresponding samples in the recording audio
file from which the clip samples were extracted, perhaps because
of some amplitude scaling performed by the detectors. This
constant specifies the maximum absolute value by which a clip
audio file sample can differ from a recording audio file sample
and still be considered the same.
"""

# clip search result codes
_CLIP_AUDIO_FILE_NOT_FOUND = 'Could not find clip audio file.'
_CLIP_SAMPLES_UNAVAILABLE = 'Could not get clip samples.'
_CLIP_AUDIO_FILE_EMPTY = 'Clip audio file is empty.'
_CLIP_SAMPLES_ALL_ZERO = 'Clip samples are all zero.'
_CLIP_NOT_FOUND = 'Could not find clip in recording.'
_CLIP_FOUND_MULTIPLE_TIMES = 'Found clip multiple times in recording.'


class AddOldBirdClipStartIndicesCommand(Command):
    
    
    extension_name = 'add_old_bird_clip_start_indices'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._dry_run = get('dry_run', args)
        
        
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()
        
        self._detectors = _get_detectors()
        
        if len(self._detectors) == 0:
            
            self._logger.info(
                'Could not find Old Bird Tseep Detector or '
                'Old Bird Thrush Detector in archive database. '
                'This command processes only clips of those detectors.')
            
        else:
            # archive includes one or both Old Bird detectors
        
            if self._dry_run:
                self._logger.info(
                    'This command is running in dry run mode. After this '
                    'message it will log the same messages that it would '
                    'during normal operation, often including messages '
                    'indicating that it is modifying the archive database. '
                    'However, it will not actually modify the database.')
                
            self._gather_recording_info()
            self._add_clip_start_indices()
            
        return True
    
    
    def _gather_recording_info(self):
        self._gather_single_recording_info()
        self._gather_multiple_recording_info()
        
        
    def _gather_single_recording_info(self):
        
        self._recordings = []
        self._recording_readers = {}
        self._channel_infos = {}
         
        for recording in self._get_recordings():
            
            files = recording.files.all().order_by('file_num')
            
            if files.count() == 0:
                # archive has no files for this recording
                
                self._logger.warning(
                    f'Archive contains no audio files for recording '
                    f'"{str(recording)}". No clips of this recording '
                    f'will be processed.')
                    
            else:
                # archive has files for this recording
                
                # Remember recording.
                self._recordings.append(recording)
                
                # Create recording reader.
                recording_reader = self._create_recording_reader(files)
                self._recording_readers[recording] = recording_reader
                
                # Gather recording channel info.
                start_time = recording.start_time
                length = recording.length
                sample_rate = recording.sample_rate
                for channel in recording.channels.all():
                    self._channel_infos[channel] = (
                        start_time, length, sample_rate, channel.channel_num,
                        recording_reader)
    
    
    def _gather_multiple_recording_info(self):
        
        self._intersecting_channels = defaultdict(list)
        
        station_night_recording_sets = self._get_station_night_recording_sets()
        
        for recordings in station_night_recording_sets:
            
            for recording in recordings:
                
                other_recordings = recordings - frozenset((recording,))
                
                for other_recording in other_recordings:
                    
                    if self._recordings_intersect(recording, other_recording):
                        
                        # self._logger.info(
                        #     f'    Recording {recording} intersects '
                        #     f'recording {other_recording}.')
                        
                        for channel in recording.channels.all():
                            
                            other_channel = other_recording.channels.get(
                                channel_num=channel.channel_num)
                            
                            self._intersecting_channels[channel].append(
                                other_channel)
    
    
    def _get_station_night_recording_sets(self):
        
        recording_sets = defaultdict(set)
        
        for recording in self._recordings:
            station = recording.station
            night = station.get_night(recording.start_time)
            recording_sets[(station, night)].add(recording)
            
        return recording_sets.values()
    
    
    def _recordings_intersect(self, a, b):
        return a.end_time >= b.start_time and a.start_time <= b.end_time
    
    
    def _get_recordings(self):
        
        try:
            return list(itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names))
            
        except Exception as e:
            self._logger.error(
                f'Collection of recordings failed with an exception.\n'
                f'The exception message was:\n'
                f'    {str(e)}\n'
                f'The archive was not modified.\n'
                f'See below for exception traceback.')
            raise
    
    
    def _get_station_recordings(self, station_name, start_date, end_date):
        
        try:
            station = Station.objects.get(name=station_name)
        except Station.DoesNotExist:
            raise CommandExecutionError(
                f'Unrecognized station "{station_name}".')
        
        time_interval = station.get_night_interval_utc(start_date, end_date)
        
        return Recording.objects.filter(
            station=station,
            start_time__range=time_interval)
    
    
    def _create_recording_reader(self, files):
        bunches = [self._create_recording_file_bunch(f) for f in files]
        return RecordingReader(bunches)
    
    
    def _create_recording_file_bunch(self, f):
        path = self._get_absolute_file_path(f.path)
        return Bunch(path=path, start_index=f.start_index, length=f.length)
    
    
    def _get_absolute_file_path(self, rel_path):
        
        rm = recording_manager
        
        try:
            return rm.get_absolute_recording_file_path(rel_path)
            
        except ValueError:
            
            dir_paths = rm.recording_dir_paths
            
            if len(dir_paths) == 1:
                s = f'the recording directory "{dir_paths[0]}"'
            else:
                path_list = str(list(dir_paths))
                s = f'any of the recording directories {path_list}'
                
            raise CommandExecutionError(
                f'Recording file "{rel_path}" could not be found in {s}.')

            
    def _add_clip_start_indices(self):
        
        start_time = time.time()
        
        self._min_start_time_change = 100
        self._max_start_time_change = -100
        
        total_clips = 0
        total_clips_found = 0
        
        for recording in self._recordings:
            
            for channel in recording.channels.all():
                
                for detector in self._detectors:
                    
                    try:
                        num_clips, num_clips_found = \
                            self._add_channel_clip_start_indices(
                                channel, detector)
                        
                    except Exception as e:
                        
                        self._logger.error(
                            f'Processing of clips for recording channel '
                            f'"{str(channel)}" failed with an exception.\n'
                            f'The exception message was:\n'
                            f'    {str(e)}\n'
                            f'No clips of the channel were modified.\n'
                            f'See below for exception traceback.')
                        
                        raise
                    
                    total_clips += num_clips
                    total_clips_found += num_clips_found
                        
        elapsed_time = time.time() - start_time
        timing_text = command_utils.get_timing_text(
            elapsed_time, total_clips, 'clips')

        self._logger.info(
            f'Added start indices for {total_clips_found} of {total_clips} '
            f'processed clips{timing_text}.')
        
        self._logger.info(
            f'Range of start time changes was '
            f'({self._min_start_time_change}, {self._max_start_time_change}).')
        
        self._log_archive_status()
    
    
    def _add_channel_clip_start_indices(self, channel, detector):
        
        recording = channel.recording
        recording_start_time = recording.start_time
        recording_length = recording.length
        sample_rate = recording.sample_rate
        
        create_count_text = text_utils.create_count_text
        
        with archive_lock.atomic():
            
            with transaction.atomic():
            
                clips = Clip.objects.filter(
                    recording_channel=channel,
                    creating_processor=detector,
                    start_index=None)
                
                num_clips = clips.count()
                num_clips_found = 0
                
                if num_clips != 0:
                    
                    count_text = create_count_text(num_clips, 'clip')
                        
                    self._logger.info(
                        f'Processing {count_text} for recording channel '
                        f'"{str(channel)}" and detector "{detector.name}"...')
                    
                    start_time = recording_start_time
                    duration = datetime.timedelta(
                        seconds=recording_length / sample_rate)
                    end_time = start_time + duration
                    
                    # self._logger.info(
                    #     f'    Recording has start time {str(start_time)} '
                    #     f'and end time {end_time}.')
                        
                    for clip in clips:
                        
                        result = self._find_clip_in_recording(clip, channel)
                        
                        if not isinstance(result, str):
                            # found clip
                            
                            # Get result parts. Note that the clip channel
                            # can change when the clip is found, since in
                            # some cases clips were attributed to the wrong
                            # recordings when the clips were imported. In
                            # one scenario, for example, a clip that was
                            # actually toward the beginning of the second
                            # of two contiguous recordings of a night was
                            # incorrectly assigned to the end of the first
                            # recording, since according to the purported
                            # start times and sample rates of the recordings
                            # the end of the first recording overlapped
                            # the start of the second recording in time.
                            samples, found_channel, start_index = result
                            
                            # Get clip start time.
                            start_seconds = start_index / sample_rate
                            delta = datetime.timedelta(seconds=start_seconds)
                            if found_channel == channel:
                                start_time = recording_start_time + delta
                            else:
                                start_time = \
                                    found_channel.recording.start_time + delta
                            
                            # Get change in clip start time.
                            start_time_change = \
                                (start_time - clip.start_time).total_seconds()
                            if start_time_change < self._min_start_time_change:
                                self._min_start_time_change = start_time_change
                            if start_time_change > self._max_start_time_change:
                                self._max_start_time_change = start_time_change

                            # Get clip length. The Old Bird detectors
                            # sometimes append zeros to a clip that were
                            # not in the recording that the clip refers
                            # to. We ignore the appended zeros.
                            length = len(samples)
                            duration = signal_utils.get_duration(
                                length, sample_rate)
                            
                            # Get clip end time.
                            end_time = signal_utils.get_end_time(
                                start_time, length, sample_rate)
                            
                            clip.channel = found_channel
                            clip.start_index = start_index
                            clip.length = length
                            clip.start_time = start_time
                            clip.end_time = end_time
                                
                            if not self._dry_run:
                                clip.save()
                            
                            num_clips_found += 1
                            
                    if num_clips_found != num_clips:
                        self._log_clips_not_found(num_clips - num_clips_found)
                        
                return num_clips, num_clips_found
    
    
    def _get_channel_info(self, channel):
        
        result = self._channel_infos.get(channel)
        
        if result is None:
            # cache miss
            
            recording = channel.recording
            start_time = recording.start_time
            length = recording.length
            sample_rate = recording.sample_rate
            channel_num = channel.channel_num
            recording_reader = self._recording_readers[recording]
            
            result = (
                start_time, length, sample_rate, channel_num,
                recording_reader)
            
            self._channel_infos[channel] = result
            
        return result
    
    
    def _find_clip_in_recording(self, clip, channel):
        
        result = self._find_clip_in_recording_aux(clip, channel)
        
        if result == _CLIP_NOT_FOUND:
                        
            channels = self._intersecting_channels.get(channel)
            
            if channels is not None:
                for channel in channels:
                    result = self._find_clip_in_recording_aux(clip, channel)
                    if not isinstance(result, str):
                        return result
                
            # If we get here, the clip was not found in an intersecting
            # channel.
            
            clip_string = _get_clip_string(clip)
            self._logger.warning(
                f'    Could not find samples of clip {clip_string} in '
                f'recording channel.')
            
            return _CLIP_NOT_FOUND
        
        else:
            return result
    
    
    def _find_clip_in_recording_aux(self, clip, channel):
        
        recording_start_time, recording_length, sample_rate, channel_num, \
            recording_reader = self._get_channel_info(channel)
        
        if not clip_manager.has_audio_file(clip):
            clip_string = _get_clip_string(clip)
            self._logger.warning(
                f'    Could not find audio file for clip {clip_string}.')
            return _CLIP_AUDIO_FILE_NOT_FOUND
        
        try:
            clip_samples = clip_manager.get_samples(clip)
        except Exception as e:
            clip_string = _get_clip_string(clip)
            self._logger.warning(
                f'    Could not get samples for clip {clip_string}. '
                f'Error message was: {str(e)}')
            return _CLIP_SAMPLES_UNAVAILABLE
        
        # For some reason, the Old Bird detectors sometimes create
        # length-zero clips, which we handle here.
        if len(clip_samples) == 0:
            clip_string = _get_clip_string(clip)
            self._logger.warning(
                f'    Audio file for clip {clip_string} has zero length')
            return _CLIP_AUDIO_FILE_EMPTY
        
        # Get start index of recording search interval.
        start_delta = clip.start_time - recording_start_time
        start_seconds = \
            start_delta.total_seconds() - _INITIAL_CLIP_SEARCH_PADDING
        search_start_index = int(round(start_seconds * sample_rate))
        
        # Get length of recording search interval.
        clip_length = len(clip_samples)
        padding_dur = _INITIAL_CLIP_SEARCH_PADDING + _FINAL_CLIP_SEARCH_PADDING
        padding_length = int(round(padding_dur * sample_rate))
        search_length = clip_length + 2 * padding_length
        
        # Adjust start index and length if search interval would start
        # before start of recording.
        if search_start_index < 0:
            search_length += search_start_index
            search_start_index = 0
        
        # Adjust length if search interval would end past end of recording.
        search_end_index = search_start_index + search_length
        if search_end_index > recording_length:
            search_length -= search_end_index - recording_length
            
        if search_start_index > recording_length or search_end_index < 0:
            # no samples in this recording to search
            
            print('Clip samples to search for do not intersect recording.')
            return _CLIP_NOT_FOUND
        
        # Read recording samples from file.
        recording_samples = recording_reader.read_samples(
            channel_num, search_start_index, search_length)
        
#         print(
#             f'Searching for length-{clip_length} clip {clip.id} in '
#             f'({search_start_index}, {search_length})...')
#         zero_count = 0
#         while clip_samples[-(zero_count + 1)] == 0:
#             zero_count += 1
#         print(f'Last ten clip samples before trailing {zero_count} zeros:')
#         for i in range(10):
#             print(f'    {clip_samples[-(zero_count + 10 + i)]}')
#         print('Last ten recording samples:')
#         for i in range(10):
#             print(f'    {recording_samples[-(10 + i)]}')
        
        match_length = clip_length
        
        if search_start_index + search_length == recording_length:
            # search interval extends to end of recording
            
            # For some reason, the Old Bird detectors sometimes append
            # zeros to a clip that extends to the end of a recording.
            # Since the zeros are not in the recording, they would
            # confound a search for the clip's samples in the recording.
            # Hence when the search interval extends to the end of the
            # recording, we initially ignore trailing zero clip samples
            # in our search. If that search is successful, we search
            # for as many of the initially-ignored zeros as might match
            # trailing recording samples below.
            
            # Adjust match length to exclude trailing zero clip samples.
            while match_length != 0 and clip_samples[match_length - 1] == 0:
                match_length -= 1
                
            if match_length == 0:
                # clip samples are all zero
                
                # This should never happen, since the Old Bird detectors
                # should never produce a clip with all zero samples.
                clip_string = _get_clip_string(clip)
                self._logger.warning(
                    f'    Encountered unexpected all-zero clip {clip_string}.')
                
                return _CLIP_SAMPLES_ALL_ZERO

        # Find clip samples in recording samples. Note that we cannot
        # just search for an exact copy of the clip samples in the
        # recording samples, since the clip samples may differ slightly
        # from the recording samples, presumably because of some scaling
        # that happens inside the Old Bird detectors. So we allow each
        # clip sample to differ from the corresponding recording sample
        # by a magnitude of up to `_CLIP_SEARCH_TOLERANCE`.
        indices = signal_utils.find_samples(
            clip_samples[:match_length], recording_samples,
            tolerance=_CLIP_SEARCH_TOLERANCE)
        
        if len(indices) == 0:
            return _CLIP_NOT_FOUND
        
        if len(indices) > 1:
            
            # For some reason, the Old Bird detectors sometimes
            # create very short clips (for example, with only one
            # sample) whose samples may occur more than once in a
            # recording. We handle such clips here.
            self._logger.warning(
                f'    Found {len(indices)} copies of length-'
                f'{clip_length} clip {clip.id} "{str(clip)}".')
            return _CLIP_FOUND_MULTIPLE_TIMES
        
        # If we get here, we found exactly one copy of the clip samples
        # in the recording.
        
        # Get start index of clip in the whole recording.
        clip_start_index = search_start_index + indices[0]
        
        if match_length != clip_length:
            # search ignored some zeros at end of clip
            
            # Check that any of the ignored trailing zero clip samples for
            # which there are corresponding trailing recording samples match
            # the recording samples.
            
            ignored_zero_count = clip_length - match_length
            search_end_index = clip_start_index + match_length
            remaining_sample_count = recording_length - search_end_index
            zero_count = min(ignored_zero_count, remaining_sample_count)
            
            if zero_count != 0:
                
                start_index = match_length
                end_index = start_index + zero_count
                diffs = recording_samples[start_index:end_index]
                
                if np.max(np.abs(diffs)) > _CLIP_SEARCH_TOLERANCE:
                    # recording samples do not match trailing zero clip samples
                    
                    return _CLIP_NOT_FOUND
                
                else:
                    # recording samples match trailing zero clip samples
                    
                    match_length += zero_count
                    
            self._logger.info(
                f'    For clip {clip.id} at end of recording, '
                f'found {match_length} of {clip_length} clip samples, '
                f'including {zero_count} trailing zeros.')
        
        # Extract clip samples from portion of recording in which
        # they were found. We return these instead of the clip file
        # samples since as explained above the recording samples
        # may differ slightly from the clip file samples.
        start_index = indices[0]
        end_index = start_index + match_length
        clip_samples = recording_samples[start_index:end_index]
        
        return clip_samples, channel, clip_start_index
    
    
    def _log_clips_not_found(self, num_clips):
        
        indices_text = 'index' if num_clips == 1 else 'indices'
        
        count_text = text_utils.create_count_text(num_clips, 'clip')
        
        self._logger.info(
            f'    Could not find start {indices_text} of {count_text} '
            f'in recording channel.')


    def _log_archive_status(self):
        
        return
    
        total_clips = Clip.objects.all().count()
        total_clips_without = Clip.objects.filter(start_index=None).count()

        if total_clips_without == 0:
            self._logger.info(
                f'At this point all {total_clips} clips of this archive '
                f'have start indices.')
            
        else:
            self._logger.info(
                f'At this point {total_clips_without} of {total_clips} '
                f'clips of this archive lack start indices.')
        
        
def _get_detectors():
    tseep = _get_detector('Old Bird Tseep Detector')
    thrush = _get_detector('Old Bird Thrush Detector')
    return [d for d in [tseep, thrush] if d is not None]


def _get_detector(name):
    try:
        return archive.get_processor(name)
    except Processor.DoesNotExist:
        return None


def _get_clip_string(clip):
    return f'{clip.id} "{str(clip)}"'
