"""Module containing class `DetectCommand`."""


from collections import defaultdict
import datetime
import itertools
import logging
import random
import time

from django.db import transaction

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import (
    Clip, Job, Processor, Recording, RecordingChannel, Station)
from vesper.old_bird.old_bird_detector_runner import OldBirdDetectorRunner
from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.singletons import extension_manager
from vesper.util.schedule import Interval, Schedule
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils


_START_STATION_NIGHT_INDEX = 10
"""Start index of station-nights for which to run detectors."""


_END_STATION_NIGHT_INDEX = 300
"""End index of station-nights for which to run detectors."""


_SCHEDULE = '''
daily:
    start_date: 2017-07-01
    end_date: 2018-12-31
    start_time: 1 hour after sunset
    end_time: 30 minutes before sunrise
'''


class DetectCommand(Command):
    
    
    extension_name = 'detect'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        self._start_station_night_index = _START_STATION_NIGHT_INDEX
        self._end_station_night_index = _END_STATION_NIGHT_INDEX
        self._schedules = {}
        
        
    def execute(self, job_info):
        
        self._job_info = job_info
        self._logger = logging.getLogger()

        detectors = self._get_detectors()
        recordings = self._get_recordings()
                
        old_bird_detectors, other_detectors = _partition_detectors(detectors)
        self._run_old_bird_detectors(old_bird_detectors, recordings)
        self._run_other_detectors(other_detectors, recordings)
            
        return True
    
    
    def _get_detectors(self):
        
        try:
            return [self._get_detector(name) for name in self._detector_names]
        
        except Exception as e:
            self._logger.error((
                'Collection of detectors to run on recordings on failed with '
                'an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise
            
            
    def _get_detector(self, name):
        try:
            return model_utils.get_processor(name, 'Detector')
        except Processor.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized detector "{}".'.format(name))
            
            
    def _get_recordings(self):
        
        try:
            
            recordings = itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names)
            
            # Collect recordings by station-night.
            recording_lists = defaultdict(list)
            for recording in recordings:
                station = recording.station
                night = station.get_night(recording.start_time)
                recording_lists[(station.name, night)].append(recording)
            
            # Sort recordings for each station-night by start time.
            for recordings in recording_lists.values():
                recordings.sort(key=lambda r: r.start_time)

            # Get list of unique station-nights.
            station_nights = sorted(recording_lists.keys())
            total_num_station_nights = len(station_nights)
            
            # self._show_station_nights(
            #     'all station-nights', station_nights, recording_lists)
            
            # Shuffle station-nights. Always seed random number generator
            # for reproducibility.
            random.seed(0)
            random.shuffle(station_nights)
            
            # Get station-nights for which to run detectors.
            start_index = self._start_station_night_index
            end_index = self._end_station_night_index
            station_nights = sorted(station_nights[start_index:end_index])
            
            # self._show_station_nights(
            #     'selected station-nights', station_nights, recording_lists)
            
            # Get all recordings for chosen station-nights.
            recordings = list(itertools.chain.from_iterable(
                recording_lists[sn] for sn in station_nights))
            recordings.sort(key=lambda r: (r.station.name, r.start_time))
            
            # self._show_recordings(recordings)
                
            self._log_intro(
                recordings, station_nights, start_index, end_index,
                total_num_station_nights)
            
            return recordings

        
        except Exception as e:
            self._logger.error((
                'Collection of recordings to run detectors on failed with '
                'an exception.\n'
                'The exception message was:\n'
                '    {}\n'
                'The archive was not modified.\n'
                'See below for exception traceback.').format(str(e)))
            raise

            
    def _get_station_recordings(self, station_name, start_date, end_date):

        # TODO: Test behavior for an unrecognized station name.
        # I tried this on 2016-08-23 and got results that did not
        # make sense to me. An exception was raised, but it appeared
        # to be  raised from within code that followed the except clause
        # in the `execute` method above (the code logged the sequence of
        # recordings returned by the `_get_recordings` method) rather
        # than from within that clause, and the error message that I
        # expected to be logged by that clause did not appear in the log.
        
        try:
            station = Station.objects.get(name=station_name)
        except Station.DoesNotExist:
            raise CommandExecutionError(
                'Unrecognized station "{}".'.format(station_name))
        
        time_interval = station.get_night_interval_utc(start_date, end_date)
        
        return Recording.objects.filter(
            station=station,
            start_time__range=time_interval)


    def _show_station_nights(self, header, station_nights, recording_lists):
        print('{}:'.format(header))
        for i, sn in enumerate(station_nights):
            station, night = sn
            print(i, station, str(night), len(recording_lists[sn]))
        print(len(station_nights))
        

    def _log_intro(
            self, recordings, station_nights, start_index, end_index,
            total_num_station_nights):
        
        self._logger.info(
            ('This command will process {} recordings for the following '
             '{} station-nights, numbers {} through {} of a total of '
             '{} station-nights.').format(
                 len(recordings), len(station_nights), start_index + 1,
                 end_index, total_num_station_nights))
        
        for station_name, night in station_nights:
            self._logger.info('    {} {}'.format(station_name, str(night)))


    def _show_recordings(self, recordings):
        print('recordings:')
        for i, r in enumerate(recordings):
            print(i, str(r))
            
            
    def _run_old_bird_detectors(self, detectors, recordings):
        
        if len(detectors) == 0:
            return
        
        for recording in recordings:
            
            recording_files = recording.files.all()
            
            if len(recording_files) == 0:
                self._logger.info(
                    'No file information available for {}.'.format(recording))
                
            else:
                num_channels = recording.num_channels
                for file_ in recording_files:
                    for channel_num in range(num_channels):
                        runner = OldBirdDetectorRunner(self._job_info)
                        runner.run_detectors(detectors, file_, channel_num)

        
    def _run_other_detectors(self, detector_models, recordings):
        
        if len(detector_models) == 0:
            return
        
        num_recordings = len(recordings)
        
        for i, recording in enumerate(recordings):
            
            self._logger.info(
                'Processing recording {} of {} - "{}"...'.format(
                    i + 1, num_recordings, str(recording)))
            
            recording_files = recording.files.all()
            
            if len(recording_files) == 0:
                self._logger.info(
                    'No file information available for {}.'.format(recording))
                
            else:
                
                recording_intervals = self._get_detection_intervals(recording)
            
                for file_ in recording_files:
                    self._run_other_detectors_on_file(
                        detector_models, file_, recording_intervals)
                    
                    
    def _get_detection_intervals(self, recording):
        
        schedule = self._get_detection_schedule(recording.station)
        
        if schedule is None:
            return [(0, recording.length)]
        
        else:
            # have schedule
            
            start_time = recording.start_time
            end_time = recording.end_time
            
            schedule_intervals = schedule.get_intervals(start_time, end_time)
            
            recording_interval = Interval(start=start_time, end=end_time)
            
            # Here we know from the contract of `Schedule.get_intervals`
            # that each interval of `schedule_intervals` intersects the
            # recording interval, so we don't have to worry about
            # `_get_time_intervals_intersection` returning `None`.
            return [
                _get_time_intervals_intersection(i, recording_interval)
                for i in schedule_intervals]
        
    
    def _get_detection_schedule(self, station):
        
        if _SCHEDULE is None:
            return None
        
        else:
            # have schedule
            
            try:
                return self._schedules[station.name]
            
            except KeyError:
                # schedule cache miss
                
                # Create schedule for this station.
                schedule = Schedule.compile_yaml(
                    _SCHEDULE, station.latitude, station.longitude,
                    station.time_zone)
                
                # Add schedule to cache.
                self._schedules[station.name] = schedule
                
                return schedule
        
            
    def _run_other_detectors_on_file(
            self, detector_models, file_, recording_intervals):
                
        if file_.path is None:
            
            self._logger.error(
                'Archive lacks path for file {} of recording {}.'.format(
                    file_.num, file_.recording))
        
        else:
            
            try:
                abs_path = model_utils.get_absolute_recording_file_path(file_)
                
            except ValueError as e:
                self._logger.error(str(e))
                
            else:
                # have absolute path of recording file
                
                reader = WaveAudioFileReader(str(abs_path))
                
                intervals = _get_file_detection_intervals(
                    file_, recording_intervals)
                
                for interval in intervals:
                    self._run_other_detectors_on_file_interval(
                        detector_models, file_, abs_path, reader, interval)
                    
                    
    def _run_other_detectors_on_file_interval(
            self, detector_models, file_, file_path, file_reader,
            time_interval):
        
        # Log detection start message.
        self._log_detection_start(
            detector_models, file_path, file_, time_interval)
                
        start_time = time.time()
        
        # Convert time interval to index interval.
        index_interval = _get_index_interval(
            time_interval, file_.start_time, file_.sample_rate)
            
        # Create detectors.
        detectors = self._create_detectors(
            detector_models, file_.recording, file_reader,
            file_.start_index + index_interval.start)
             
        # Detect.
        for samples in _generate_sample_buffers(file_reader, index_interval):
            for detector in detectors:
                channel_samples = samples[detector.channel_num]
                detector.detect(channel_samples)
                 
        # Wrap up detection.
        for detector in detectors:
            detector.complete_detection()

        processing_time = time.time() - start_time
        
        # Log detection performance message.
        interval_duration = \
            (time_interval.end - time_interval.start).total_seconds()
        self._log_detection_performance(
            len(detector_models), file_.num_channels, interval_duration,
            processing_time)
                    
                
    def _log_detection_start(
            self, detector_models, file_path, file_, time_interval):
         
        if time_interval.start == file_.start_time and \
                time_interval.end == file_.end_time:
            # running detectors on entire file
             
            interval_text = ''
             
        else:
            # not running detectors on entire file
            
            start = _format_datetime(time_interval.start)
            end = _format_datetime(time_interval.end)
            
            if time_interval.start == file_.start_time:
                # interval includes file start
                
                interval_text = ' interval [file start, {}]'.format(end)
                
            elif time_interval.end == file_.end_time:
                # interval includes file end
                
                interval_text = ' interval [{}, file end]'.format(start)
                
            else:
                # interval includes neither file start nor file end
                
                interval_text = ' interval [{}, {}]'.format(start, end)                 
             
        suffix = '' if len(detector_models) == 1 else 's'
        
        self._logger.info(
            'Running detector{} on file "{}"{}...'.format(
                suffix, file_path, interval_text))
        

    def _create_detectors(
            self, detector_models, recording, file_reader,
            interval_start_index):
        
        num_channels = recording.num_channels
        
        detectors = []
        
        job = Job.objects.get(id=self._job_info.job_id)

        for detector_model in detector_models:
            
            for channel_num in range(num_channels):
                
                recording_channel = RecordingChannel.objects.get(
                    recording=recording, channel_num=channel_num)
                
                listener = _DetectorListener(
                    detector_model, recording, recording_channel,
                    file_reader, interval_start_index, job, self._logger)
                
                detector = _create_detector(
                    detector_model, recording, listener)
                
                # We add a `channel_num` attribute to each detector to keep
                # track of which recording channel it is for.
                detector.channel_num = channel_num
                
                detectors.append(detector)
            
        return detectors


    def _log_detection_performance(
            self, num_detectors, num_channels, interval_duration,
            processing_time):
        
        format_ = text_utils.format_number
        
        dur = format_(interval_duration)
        time = format_(processing_time)
        
        suffix = '' if num_detectors == 1 else 's'
        message = (
            'Ran {} detector{} on {} seconds of {}-channel audio in {} '
            'seconds').format(num_detectors, suffix, dur, num_channels, time)
        
        if processing_time != 0:
            total_duration = num_detectors * num_channels * interval_duration
            speedup = format_(total_duration / processing_time)
            message += ', {} times faster than real time.'.format(speedup)
        else:
            message += '.'
            
        self._logger.info(message)
        

# This module must be able to distinguish between the original Old Bird
# Tseep and Thrush detectors and other detectors since there are special
# considerations for running the Old Bird detectors. We will probably
# eventually drop support for the original Old Bird detectors, at which
# point we can be rid of this ugliness.
_OLD_BIRD_DETECTOR_NAMES = (
    'Old Bird Thrush Detector',
    'Old Bird Tseep Detector'
)


def _partition_detectors(detectors):
    
    old_bird_detectors = []
    other_detectors = []
    
    for detector in detectors:
        
        if detector.name in _OLD_BIRD_DETECTOR_NAMES:
            old_bird_detectors.append(detector)
            
        else:
            other_detectors.append(detector)
            
    return (old_bird_detectors, other_detectors)


def _get_time_intervals_intersection(a, b):
    
    if a.end < b.start or b.end < a.start:
        # intervals do not intersect
        
        return None
    
    else:
        # intervals intersect
        
        start = a.start if b.start < a.start else b.start
        end = a.end if a.end < b.end else b.end
        return Interval(start=start, end=end)


def _get_file_detection_intervals(file_, recording_intervals):
    
    """Gets the sound file index intervals on which to run detectors."""
    
    file_interval = Interval(file_.start_time, file_.end_time)
    
    detection_intervals = [
        _get_time_intervals_intersection(i, file_interval)
        for i in recording_intervals]
    
    # Remove any `None` elements from detection intervals list.
    detection_intervals = [i for i in detection_intervals if i is not None]
    
    return detection_intervals
    

def _get_index_interval(time_interval, start_time, sample_rate):
    
    """
    Gets the sound file index interval corresponding to the specified
    time interval.
    """
    
    start_offset = (time_interval.start - start_time).total_seconds()
    start_index = signal_utils.seconds_to_frames(start_offset, sample_rate)
    
    duration = (time_interval.end - time_interval.start).total_seconds()
    length = signal_utils.seconds_to_frames(duration, sample_rate)
    
    return Interval(start=start_index, end=start_index + length)


def _get_index_intervals_intersection(a, b):
    
    if a.end <= b.start or b.end <= a.start:
        # intervals do not intersect
        
        return None
    
    else:
        # intervals intersect
        
        start = a.start if b.start < a.start else b.start
        end = a.end if a.end < b.end else b.end
        return Interval(start=start, end=end)
    
    
def _generate_sample_buffers(file_reader, interval):
    
    chunk_size = 100000
    
    index = interval.start
    end_index = interval.end
    
    while index != end_index:
        length = min(chunk_size, end_index - index)
        yield file_reader.read(index, length)
        index += length
        
        
def _format_datetime(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S UTC')


# TODO: Who is the authority regarding detectors: `Processor` instances
# or the extension manager? Right now detector names are stored redundantly
# in both `Processor` instances and the extensions, and hence there is
# the potential for inconsistency. We populate UI controls from the
# `Processor` instances, but construct detectors using the extension
# manager, which finds extensions using the names stored in the extensions
# themselves. How might we eliminate the redundancy? Be sure to consider
# versioning and the possibility of processing parameters when thinking
# about this.
def _create_detector(detector_model, recording, listener):
    
    detector_name = detector_model.name
    
    classes = extension_manager.instance.get_extensions('Detector')
    
    try:
        cls = classes[detector_name]
    except KeyError:
        raise ValueError('Unrecognized detector "{}".'.format(detector_name))
    
    return cls(recording.sample_rate, listener)


class _DetectorListener:
    
    
    def __init__(
            self, detector_model, recording, recording_channel, file_reader,
            interval_start_index, job, logger):
        
        self._detector_model = detector_model
        self._recording = recording
        self._recording_channel = recording_channel
        self._file_reader = file_reader
        self._interval_start_index = interval_start_index
        self._job = job
        self._logger = logger
        self._clips = []
        
        
    def process_clip(self, start_index, length, threshold=None):
        self._clips.append((start_index, length))
        
        
    def complete_processing(self, threshold=None):
        
        self._logger.info(
            'Writing {} clips to database for detector "{}"...'.format(
                len(self._clips), self._detector_model.name))
        
        station = self._recording.station
        recording_channel = self._recording_channel
        mic_output = recording_channel.mic_output
        detector_model = self._detector_model
        
        sample_rate = self._recording.sample_rate
        
        creation_time = time_utils.get_utc_now()
        
        with transaction.atomic():
            
            for start_index, length in self._clips:
                
                # Get clip start time as a `datetime`.
                start_index += self._interval_start_index
                start_delta = datetime.timedelta(
                    seconds=start_index / sample_rate)
                start_time = self._recording.start_time + start_delta
                
                end_time = signal_utils.get_end_time(
                    start_time, length, sample_rate)
            
                Clip.objects.create(
                    station=station,
                    mic_output=mic_output,
                    recording_channel=recording_channel,
                    start_index=start_index,
                    length=length,
                    sample_rate=sample_rate,
                    start_time=start_time,
                    end_time=end_time,
                    date=station.get_night(start_time),
                    creation_time=creation_time,
                    creating_user=None,
                    creating_job=self._job,
                    creating_processor=detector_model
                )
