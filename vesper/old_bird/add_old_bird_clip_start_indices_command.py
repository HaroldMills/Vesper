"""Module containing class `AddOldBirdClipStartIndicesCommand`."""


import datetime
import itertools
import logging
import time

from django.db import transaction

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import Clip, Processor, Recording, Station
from vesper.old_bird.recording_reader import RecordingReader
from vesper.singletons import archive, clip_manager, recording_manager
from vesper.util.bunch import Bunch
import vesper.command.command_utils as command_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.signal_utils as signal_utils
import vesper.util.text_utils as text_utils


_CLIP_SEARCH_PADDING = 5
"""
Padding for recording clip search, in seconds.

Since the Old Bird detectors only provide an approximate start time
of a clip in a recording (as an integer number of seconds from the
start of the recording), to find the exact index of a clip in a
recording we must search for the clip in the recording. We do this
by searching for the clip in the portion of the recording that starts
`_CLIP_SEARCH_PADDING` seconds before the approximate clip start time
and whose duration is the clip duration plus twice the padding.

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
        self._clip_manager = clip_manager.instance
        
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
                
            recordings = self._get_recordings()  
            self._add_clip_start_indices(recordings)
            
        return True
    
    
    def _get_recordings(self):
        
        try:
            return list(itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names))
            
        except Exception as e:
            self._logger.error((
                'Collection of recordings failed with an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

            
    def _get_station_recordings(self, station_name, start_date, end_date):

        try:
            station = Station.objects.get(name=station_name)
        except Station.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized station "{}".'.format(station_name))
        
        time_interval = station.get_night_interval_utc(start_date, end_date)
        
        return Recording.objects.filter(
            station=station,
            start_time__range=time_interval)


    def _add_clip_start_indices(self, recordings):
        
        start_time = time.time()
        
        total_clips = 0
        total_clips_found = 0
        
        for recording in recordings:
            
            files = recording.files.all().order_by('file_num')
        
            if files.count() == 0:
                # archive has no files for this recording
                
                self._logger.warning(
                    f'Archive contains no audio files for recording '
                    f'"{str(recording)}". No clips of this recording '
                    f'will be processed.')
                
            else:
                # archive has files for this recording
                
                self._recording_reader = self._create_recording_reader(files)
                
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
        
        self._log_archive_status()


    def _create_recording_reader(self, files):
        bunches = [self._create_recording_file_bunch(f) for f in files]
        return RecordingReader(bunches)
    
    
    def _create_recording_file_bunch(self, f):
        path = self._get_absolute_file_path(f.path)
        return Bunch(path=path, start_index=f.start_index, length=f.length)

        
    def _get_absolute_file_path(self, rel_path):
        
        manager = recording_manager.instance
        
        try:
            return manager.get_absolute_recording_file_path(rel_path)
            
        except ValueError:
            
            dir_paths = manager.recording_dir_paths
            
            if len(dir_paths) == 1:
                s = f'the recording directory "{dir_paths[0]}"'
            else:
                path_list = str(list(dir_paths))
                s = f'any of the recording directories {path_list}'
                
            raise CommandExecutionError(
                f'Recording file "{rel_path}" could not be found in {s}.')

            
    def _add_channel_clip_start_indices(self, channel, detector):
        
        # Stash some data as object attributes so we don't have to
        # repeatedly pass them to `_find_clip_in_recording_channel`
        # method or query database there.
        recording = channel.recording
        self._recording_start_time = recording.start_time
        self._recording_length = recording.length
        self._sample_rate = recording.sample_rate
        self._channel_num = channel.channel_num
                    
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
                        f'"{str(channel)}" and detector "{detector.name}...')
                        
                    for clip in clips:
                        
                        result = self._find_clip_in_recording_channel(clip)
                        
                        if result is not None:
                            
                            start_index = result[1]
                            
                            start_seconds = start_index / self._sample_rate
                            delta = datetime.timedelta(seconds=start_seconds)
                            start_time = self._recording_start_time + delta
                            
                            end_time = signal_utils.get_end_time(
                                start_time, clip.length, self._sample_rate)
                            
                            start_time_change = \
                                (start_time - clip.start_time).total_seconds()
                                
                            duration = (clip.length - 1) / self._sample_rate
                            
                            self._logger.info(
                                f'    {start_index} {str(clip.start_time)} '
                                f'-> {str(start_time)} {start_time_change} '
                                f'{duration} {str(end_time)}')
                            
                            clip.start_index = start_index
                            clip.start_time = start_time
                            clip.end_time = end_time
                                
                            if not self._dry_run:
                                clip.save()
                            
                            num_clips_found += 1
                            
                    if num_clips_found != num_clips:
                        self._log_clips_not_found(num_clips - num_clips_found)
                        
                return num_clips, num_clips_found


    def _index_to_time(self, index):
        seconds = index / self._sample_rate
        delta = datetime.timedelta(seconds=seconds)
        return self._recording_start_time + delta


    def _find_clip_in_recording_channel(self, clip):
        
        if not clip_manager.instance.has_audio_file(clip):
            self._logger.warning(
                f'    Could not find audio file for clip "{str(clip)}".')
            return None
        
        try:
            clip_samples = clip_manager.instance.get_samples(clip)
        except Exception as e:
            self._logger.warning(
                f'    Could not get samples for clip "{str(clip)}". '
                f'Error message was: {str(e)}')
            return None
        
        # For some reason, the Old Bird detectors sometimes create
        # length-zero clips, which we handle here.
        if len(clip_samples) == 0:
            self._logger.warning(
                f'    Audio file for clip "{str(clip)}" has zero length.')
            return None
        
        start_delta = clip.start_time - self._recording_start_time
        start_seconds = start_delta.total_seconds() - _CLIP_SEARCH_PADDING
        start_index = int(round(start_seconds * self._sample_rate))
        
        padding_length = int(round(_CLIP_SEARCH_PADDING * self._sample_rate))
        length = len(clip_samples) + 2 * padding_length
        
        # Adjust start index and length if search interval would extend
        # past start of file.
        if start_index < 0:
            length += start_index
            start_index = 0
        
        # Adjust length if search interval would extend past end of recording.
        end_index = start_index + length
        if end_index > self._recording_length:
            length -= end_index - self._recording_length

        # Read recording samples from file.
        recording_samples = self._recording_reader.read_samples(
            self._channel_num, start_index, length)
        
        # Find clip in recording samples. Note that we cannot just search
        # for an exact copy of the clip samples in the recording samples,
        # since the clip samples may differ slightly from the recording
        # samples, presumably because of some scaling that happens inside
        # the Old Bird detectors. So we allow each clip sample to differ
        # from the corresponding recording sample by a magnitude of up to
        # one.
        indices = signal_utils.find_samples(
            clip_samples, recording_samples, tolerance=_CLIP_SEARCH_TOLERANCE)
        
        if len(indices) == 0:
            self._logger.warning(
                f'    Could not find samples of clip "{str(clip)}" in '
                f'recording channel.')
            return None
        
        else:
            # found clip samples in recording samples
            
            if len(indices) > 1:
                
                # For some reason, the Old Bird detectors sometimes
                # create very short clips (for example, with only one
                # sample) whose samples may occur more than once in a
                # recording. We handle such clips here.
                self._logger.warning(
                    f'    Found {len(indices)} copies of length-'
                    f'{clip.length} clip "{str(clip)}".')
                return None
                
            # Get start index of clip in the whole recording.
            clip_start_index = start_index + indices[0]
                
            # Extract clip samples from portion of recording in which
            # they were found. We return these instead of the clip file
            # samples since as explained above the recording samples
            # may differ slightly from the clip file samples.
            start_index = indices[0]
            end_index = start_index + len(clip_samples)
            clip_samples = recording_samples[start_index:end_index]
            
            return (clip_samples, clip_start_index)
        
        
    def _log_clips_not_found(self, num_clips):
        
        indices_text = 'index' if num_clips == 1 else 'indices'
        
        count_text = text_utils.create_count_text(num_clips, 'clip')
        
        self._logger.info(
            f'    Could not find start {indices_text} of {count_text} '
            f'in recording channel.')


    def _log_archive_status(self):
        
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
        return archive.instance.get_processor(name)
    except Processor.DoesNotExist:
        return None
