"""Module containing class `DetectCommand`."""


import datetime
import itertools
import logging
import os.path
import time

from django.db import transaction

from vesper.command.command import Command, CommandExecutionError
from vesper.django.app.models import (
    Clip, Job, Processor, Recording, RecordingChannel, Station)
from vesper.old_bird.old_bird_detector_runner import OldBirdDetectorRunner
from vesper.signal.wave_audio_file import WaveAudioFileReader
from vesper.singletons import extension_manager
import vesper.command.command_utils as command_utils
import vesper.django.app.model_utils as model_utils
import vesper.util.archive_lock as archive_lock
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils


class DetectCommand(Command):
    
    
    extension_name = 'detect'
    
    
    def __init__(self, args):
        super().__init__(args)
        get = command_utils.get_required_arg
        self._detector_names = get('detectors', args)
        self._station_names = get('stations', args)
        self._start_date = get('start_date', args)
        self._end_date = get('end_date', args)
        
        
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
            return list(itertools.chain.from_iterable(
                self._get_station_recordings(
                    name, self._start_date, self._end_date)
                for name in self._station_names))
            
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
        
        for recording in recordings:
                    
            recording_files = recording.files.all()
            
            if len(recording_files) == 0:
                self._logger.info(
                    'No file information available for {}.'.format(recording))
                
            else:
                
                for file_ in recording_files:
                    self._run_other_detectors_on_file(detector_models, file_)
                    
                    
    def _run_other_detectors_on_file(self, detector_models, file_):
                
        recording = file_.recording
        
        if file_.path is None:
            
            self._logger.info(
                'Path missing for file {} of recording {}.'.format(
                    file_.num, recording))
        
        else:
            
            try:
                abs_path = model_utils.get_recording_file_absolute_path(file_)
                
            except ValueError as e:
                self._logger.error(str(e))
                
            else:
                
                self._log_detection_start(detector_models, abs_path)
                
                start_time = time.time()
                
                file_reader = WaveAudioFileReader(str(abs_path))
                
                detectors = self._create_detectors(
                    detector_models, recording, file_reader,
                    file_.start_index)
            
                for samples in _generate_sample_buffers(abs_path):
                    for detector in detectors:
                        channel_samples = samples[detector.channel_num]
                        detector.detect(channel_samples)
                        
                for detector in detectors:
                    detector.complete_detection()
                    
                processing_time = time.time() - start_time
                
                file_duration = file_.length / recording.sample_rate
    
                self._log_detection_performance(
                    len(detector_models), recording.num_channels,
                    file_duration, processing_time)
                    
                
    def _log_detection_start(self, detector_models, file_path):
        
        if len(detector_models) == 1:
            
            self._logger.info(
                'Running detector "{}" on file "{}"...'.format(
                    detector_models[0].name, file_path))
            
        else:
            
            self._logger.info(
                'Running the following detectors on file "{}"...'.format(
                    file_path))
            
            for model in detector_models:
                self._logger.info('    {}'.format(model.name))
                

    # TODO: Do we really need to pass both the recording and the recording
    # file around? How many extra queries do we incur if we don't?
    
    
    def _create_detectors(
            self, detector_models, recording, file_reader, file_start_index):
        
        num_channels = recording.num_channels
        
        detectors = []
        
        job = Job.objects.get(id=self._job_info.job_id)

        for detector_model in detector_models:
            
            for channel_num in range(num_channels):
                
                recording_channel = RecordingChannel.objects.get(
                    recording=recording, channel_num=channel_num)
                
                listener = _DetectorListener(
                    detector_model, recording, recording_channel,
                    file_reader, file_start_index, job, self._logger)
                
                detector = _create_detector(
                    detector_model, recording, listener)
                
                # We add a `channel_num` attribute to each detector to keep
                # track of which recording channel it is for.
                detector.channel_num = channel_num
                
                detectors.append(detector)
            
        return detectors


    def _log_detection_performance(
            self, num_detectors, num_channels, file_duration, processing_time):
        
        format_ = text_utils.format_number
        
        dur = format_(file_duration)
        time = format_(processing_time)
        
        suffix = '' if num_detectors == 1 else 's'
        message = (
            'Ran {} detector{} on {}-channel, {}-second file in {} '
            'seconds').format(num_detectors, suffix, num_channels, dur, time)
        
        if processing_time != 0:
            dcs = num_detectors * num_channels * file_duration
            speedup = format_(dcs / processing_time)
            message += ', {} times faster than real time.'.format(speedup)
        else:
            message += '.'
            
        self._logger.info(message)
        

def _generate_sample_buffers(path):
    
    chunk_size = 1000000
    
    reader = WaveAudioFileReader(str(path))
    start_index = 0
    
    while start_index < reader.length:
        length = min(chunk_size, reader.length - start_index)
        yield reader.read(start_index, length)
        start_index += chunk_size
        
        
class _DetectorListener:
    
    
    def __init__(
            self, detector_model, recording, recording_channel, file_reader,
            file_start_index, job, logger):
        
        self._detector_model = detector_model
        self._recording = recording
        self._recording_channel = recording_channel
        self._file_reader = file_reader
        self._file_start_index = file_start_index
        self._job = job
        self._logger = logger
        
        
    def process_clip(self, start_index, length):
        
        station = self._recording.station
        
        sample_rate = self._recording.sample_rate
        
        # Get clip start time as a `datetime`.
        start_index += self._file_start_index
        start_delta = datetime.timedelta(seconds=start_index / sample_rate)
        start_time = self._recording.start_time + start_delta
        
        end_time = signal_utils.get_end_time(start_time, length, sample_rate)
        
        creation_time = time_utils.get_utc_now()
        
        try:
            
            with archive_lock.atomic():
                
                with transaction.atomic():
                    
                    clip = Clip.objects.create(
                        station=station,
                        mic_output=self._recording_channel.mic_output,
                        recording_channel=self._recording_channel,
                        start_index=start_index,
                        length=length,
                        sample_rate=sample_rate,
                        start_time=start_time,
                        end_time=end_time,
                        date=station.get_night(start_time),
                        creation_time=creation_time,
                        creating_user=None,
                        creating_job=self._job,
                        creating_processor=self._detector_model
                    )
                    
                    # We must create the clip sound file after creating
                    # the clip row in the database. The file's path
                    # depends on the clip ID, which is set as part of
                    # creating the clip row.
                    #
                    # We create the sound file within the database
                    # transaction to ensure that the clip row and
                    # sound file are created atomically.
                    self._create_clip_sound_file(clip)
                
        except Exception as e:
            mic_output_name = self._recording_channel.mic_output.name
            detector = self._detector_model
            detector_name = 'None' if detector is None else detector.name
            duration = signal_utils.get_duration(length, sample_rate)
            s = Clip.get_string(
                station.name, mic_output_name, detector_name, start_time,
                duration)
            self._logger.error((
                'Attempt to archive clip {} failed with message: {}. '
                'Clip will be ignored.').format(s, str(e)))
        
        else:
            self._logger.info('Archived clip {}.'.format(clip))


    def _create_clip_sound_file(self, clip):
        
        # Create clip directory if needed.
        dir_path = os.path.dirname(clip.wav_file_path)
        os_utils.create_directory(dir_path)

        path = clip.wav_file_path
        start_index = clip.start_index - self._file_start_index
        samples = self._file_reader.read(start_index, clip.length)
        samples = samples[self._recording_channel.channel_num]
        samples.shape = (1, clip.length)
        audio_file_utils.write_wave_file(path, samples, clip.sample_rate)
    
    
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
