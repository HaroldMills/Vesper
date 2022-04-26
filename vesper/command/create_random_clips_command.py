"""Module containing class `CreateRandomClipsCommand`."""


from datetime import timedelta as TimeDelta
import logging

import django.db
import numpy as np

from vesper.command.command import Command
from vesper.django.app.models import Clip, Job, Processor, RecordingChannel
from vesper.singleton.archive import archive
from vesper.singleton.preset_manager import preset_manager
from vesper.util.schedule import Interval, Schedule
import vesper.command.command_utils as command_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


_PROCESSOR_NAME = 'Vesper Random Clip Creator 1.0'
_PROCESSOR_TYPE = 'Clip Creator'
_PROCESSOR_DESCRIPTION = '''
Virtual processor created by Vesper's Create Random Clips command.
The Create Random Clips command assigns this processor as the
creating processor of each clip that it creates.
'''.lstrip()


_logger = logging.getLogger()


# TODO: Consider avoiding collisions across multiple runs of this command.

# TODO: Consider optionally avoiding creating clips that intersect
# specified existing ones, e.g. Call* clips. The command might do this
# by excluding the intervals of the specified clips from consideration
# for random clip creation.


class CreateRandomClipsCommand(Command):
    
    
    extension_name = 'create_random_clips'
    
    
    def __init__(self, args):
        
        super().__init__(args)
        
        get = command_utils.get_required_arg
        self._sm_pair_ui_names = get('station_mics', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._schedule_name = get('schedule', args)
        self._clip_duration = get('clip_duration', args)
        self._clip_count = get('clip_count', args)
        
        self._schedule_preset = _get_schedule_preset(self._schedule_name)
        if self._schedule_preset is None:
            self._schedule_cache = None
        else:
            self._schedule_cache = _ScheduleCache(self._schedule_preset)

        self._clip_creator = _ClipCreator()
        
        
    def execute(self, job_info):
        
        # django.db.reset_queries()

        self._job_info = job_info

        _logger.info(
            'Gathering information about recording channel intervals in '
            'which to create clips...')

        # Get recording channel intervals in which to create clips,
        # as specified by command arguments.
        sm_pairs = command_utils.get_station_mic_output_pairs(
            self._sm_pair_ui_names)
        intervals = _get_processing_intervals(
            sm_pairs, self._start_date, self._end_date, self._schedule_cache)

        # Get subset of intervals that are *usable* in the sense that
        # they are long enough to contain a clip of duration
        # `self._clip_duration`. Also get time bounds of usable portions
        # of usable intervals in the concatenation of the usable portions.
        # The *usable portion* of a usable interval is the portion of
        # the interval in which a clip of duration `self._clip_duration`
        # can start and still be contained in the interval, i.e. the
        # initial portion ending `self._clip_duration` seconds before
        # the end of the interval. The length of the time bounds array
        # is one more than the number of usable intervals. Element i
        # of the array is the start time of interval i and the end
        # time of interval i - 1, in seconds from the start of the
        # concatenation.
        usable_intervals, time_bounds = \
            _get_concatenated_time_bounds(intervals, self._clip_duration)

        _logger.info('Generating random clip start times...')

        # Get start offsets of random clips in concatenation of usable
        # interval portions, in seconds.
        start_offsets = np.random.uniform(
            time_bounds[0], time_bounds[-1], self._clip_count)

        # Sort start offsets so they are in ascending order. We don't
        # have to do this for the call to `np.searchsorted` below to
        # work, but it seems like a good idea so we can create the
        # clips in a sensible order.
        start_offsets.sort()

        # Get index of usable interval of each clip.
        interval_indices = \
            np.searchsorted(time_bounds, start_offsets, 'right') - 1


        # Create clips.

        creation_time = time_utils.get_utc_now()
        creating_processor = self._get_creating_processor()
        creating_job = Job.objects.get(pk=self._job_info.job_id)

        _logger.info('Creating clips ...')

        # Bookkeeping for start index collision detection and resolution.
        last_interval_num = -1
        used_start_indices = set()

        for i, start_offset in zip(interval_indices, start_offsets):

            station, channel, interval_start_time, interval_end_time = \
                usable_intervals[i]
            recording = channel.recording
            sample_rate = recording.sample_rate

            # Get clip start index in recording.
            start_offset = TimeDelta(seconds=start_offset - time_bounds[i])
            start_time = interval_start_time + start_offset
            start_index = signal_utils.time_to_index(
                start_time, recording.start_time, sample_rate)

            # Get clip length in samples.
            length = signal_utils.seconds_to_frames(
                self._clip_duration, sample_rate)

            if i != last_interval_num:
                # new interval

                last_interval_num = i
                used_start_indices.clear()

            elif start_index in used_start_indices:
                # start index collision

                interval_end_index = signal_utils.time_to_index(
                    interval_end_time, interval_start_time, sample_rate)

                start_index = self._resolve_start_index_collision(
                    start_index, length, used_start_indices,
                    interval_end_index)

                if start_index is None:

                    _logger.warning(
                        'Could not resolve clip start index collision '
                        'while creating random clips in recording channel '
                        f'{str(channel)}. Clip for which collision '
                        'could not be resolved will not be created.')

                    # Move on to next clip.
                    continue

            # Get time of first clip sample.
            start_time = signal_utils.index_to_time(
                start_index, recording.start_time, sample_rate)

            # Get time of last clip sample.
            end_time = \
                signal_utils.get_end_time(start_time, length, sample_rate)

            date = station.get_night(start_time)

            clip = Clip(
                station=station,
                mic_output=channel.mic_output,
                recording_channel=channel,
                start_index=start_index,
                length=length,
                sample_rate=sample_rate,
                start_time=start_time,
                end_time=end_time,
                date=date,
                creation_time=creation_time,
                creating_processor=creating_processor,
                creating_job=creating_job)

            self._clip_creator.add_clip(clip)

            used_start_indices.add(start_index)

        # Make sure to create all clips.
        self._clip_creator.flush()

        # _show_queries('create_random_clips')

        return True


    def _get_creating_processor(self):

        try:
            processor = Processor.objects.get(
                name=_PROCESSOR_NAME, type=_PROCESSOR_TYPE)

        except Processor.DoesNotExist:

            _logger.info(f'Creating processor "{_PROCESSOR_NAME}"...')

            processor = Processor.objects.create(
                name=_PROCESSOR_NAME,
                type=_PROCESSOR_TYPE,
                description=_PROCESSOR_DESCRIPTION
            )

            archive.refresh_processor_cache()

        return processor


def _get_schedule_preset(schedule_name):
    
    if schedule_name == archive.NULL_CHOICE:
        # no schedule specified

        return None
    
    else:
        # schedule specified
        
        preset_path = ('Detection Schedule', schedule_name)
        preset = preset_manager.get_preset(preset_path)
        return preset.data


def _get_processing_intervals(sm_pairs, start_date, end_date, schedule_cache):

    processing_intervals = []

    for station, mic_output in sm_pairs:

        start_time, end_time = \
            station.get_night_interval_utc(start_date, end_date)

        channels = RecordingChannel.objects.filter(
            recording__station=station,
            mic_output=mic_output,
            recording__start_time__lt=end_time,
            recording__end_time__gt=start_time
        ).select_related('recording')

        if schedule_cache is None:
            schedule = None
        else:
            schedule = schedule_cache.get_schedule(station)

        for channel in channels:

            # Get time intervals to process for channel.
            intervals = _get_channel_intervals(channel, schedule)

            # Prepend other information to intervals.
            intervals = [(station, channel) + i for i in intervals]

            processing_intervals.extend(intervals)

    processing_intervals.sort(key=_create_interval_key)

    return processing_intervals


def _get_channel_intervals(channel, schedule):

    recording = channel.recording
    start_time = recording.start_time
    end_time = recording.end_time

    if schedule is None:
        return [(start_time, end_time)]

    else:
        # have schedule

        schedule_intervals = schedule.get_intervals(start_time, end_time)
        recording_interval = Interval(start=start_time, end=end_time)
        
        # Here we know from the contract of `Schedule.get_intervals`
        # that each interval of `schedule_intervals` intersects the
        # recording interval, so we don't have to worry about
        # `_get_time_intervals_intersection` returning `None`.
        return [
            _get_time_intervals_intersection(i, recording_interval)
            for i in schedule_intervals]


def _get_time_intervals_intersection(a, b):
    
    if a.end < b.start or b.end < a.start:
        # intervals do not intersect
        
        return None
    
    else:
        # intervals intersect
        
        start = a.start if b.start < a.start else b.start
        end = a.end if a.end < b.end else b.end
        return (start, end)


def _create_interval_key(interval):
    station, channel, start_time, _ = interval
    return (
        station.name, channel.recording.start_time, channel.channel_num,
        start_time)

        
def _get_concatenated_time_bounds(intervals, clip_duration):

   # The work of this function is divided as it is to make it easier
    # to unit test the `_get_concatenated_time_bounds_aux` function.

    # Prepare intervals for `_get_concatenated_time_bounds_aux`.
    diddled_intervals = _diddle_intervals(intervals)

    # Figure out which intervals are long enough to create clips in,
    # and get the time bounds of the portions of ths intervals in
    # which clips can start in their concatenation.
    usable_interval_indices, time_bounds = \
        _get_concatenated_time_bounds_aux(diddled_intervals, clip_duration)

    # Get usable intervals from indices.
    usable_intervals = [intervals[i] for i in usable_interval_indices]

    return usable_intervals, time_bounds

    
def _diddle_intervals(intervals):
    return [_diddle_interval(i) for i in intervals]


def _diddle_interval(interval):
    _, channel, start_time, end_time = interval
    recording = channel.recording
    sample_rate = recording.sample_rate
    recording_start_time = recording.start_time
    return recording_start_time, sample_rate, start_time, end_time

    
def _get_concatenated_time_bounds_aux(intervals, clip_duration):

    s2f = signal_utils.seconds_to_frames
    f2s = signal_utils.get_duration

    usable_interval_indices = []
    time_bounds = []
    last_end_time = 0.

    for i, interval in enumerate(intervals):

        recording_start_time, sample_rate, start_time, end_time = interval


        # Get usable subinterval length in samples. Work in samples
        # instead of in seconds to ensure that a clip of the desired
        # length will be entirely contained in the interval if it
        # starts in what we decide is the usable subinterval.

        offset = (start_time - recording_start_time).total_seconds()
        start_index = s2f(offset, sample_rate)

        offset = (end_time - recording_start_time).total_seconds()
        end_index = s2f(offset, sample_rate)

        interval_length = end_index - start_index

        clip_length = s2f(clip_duration, sample_rate)

        usable_length = interval_length - clip_length


        if usable_length > 0:
            # interval is longer than clip length

            usable_interval_indices.append(i)
            time_bounds.append(last_end_time)

            usable_duration = f2s(usable_length, sample_rate)
            last_end_time += usable_duration

    time_bounds.append(last_end_time)

    return usable_interval_indices, np.array(time_bounds)


def _resolve_start_index_collision(
        start_index, length, used_start_indices, interval_end_index):

    # This method tries to resolve a start index collision, first
    # by looking for a later usable start index and then, if none
    # is available, for an earlier one. For reasonable random clip
    # densities, the next start index will almost always be available
    # so this method will just return that.

    # Find first start index after `start_index` that is unused.
    # This will usually be the next index, but might not be if other
    # collisions for this same start index have already been resolved.
    new_start_index = start_index + 1
    while new_start_index in used_start_indices:
        new_start_index += 1

    if new_start_index + length <= interval_end_index:
        # clip with this start index fits in interval

        return new_start_index

    # If we get here, there are no unused start indices for this interval
    # after `start_index`.

    # Find first start index before `start_index` that is unused.
    new_start_index = start_index - 1
    while new_start_index in used_start_indices:
        new_start_index -= 1

    if new_start_index >= 0:
        return new_start_index

    # If we get here, there are no unused start indices for this interval!
    return None


def _show_queries(name):
    connection = django.db.connection
    queries = connection.queries
    print(f'{name} performed {len(queries)} queries:')
    for i, query in enumerate(connection.queries):
        print(f'    {i}: {query}')


class _ScheduleCache:


    def __init__(self, schedule_spec):
        self._schedule_spec = schedule_spec
        self._schedules = {}


    def get_schedule(self, station):

        try:
            return self._schedules[station.name]
        
        except KeyError:
            # cache miss
            
            if _logger is not None:
                _logger.info(
                    f'Compiling schedule for station "{station.name}"...')

            # Compile schedule for this station.
            schedule = Schedule.compile_dict(
                self._schedule_spec, station.latitude, station.longitude,
                station.time_zone)
            
            # Add schedule to cache.
            self._schedules[station.name] = schedule
            
            return schedule


class _ClipCreator:


    def __init__(self, batch_size=50):
        self._batch_size = batch_size
        self._clips = []


    def add_clip(self, clip):
        self._clips.append(clip)
        if len(self._clips) == self._batch_size:
            self.flush()


    def flush(self):
        if len(self._clips) != 0:
            Clip.objects.bulk_create(self._clips)
            self._clips.clear()
