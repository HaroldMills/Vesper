"""Module containing class `OldBirdDetectorRunner`."""


from threading import Thread
import datetime
import logging
import os.path
import re
import subprocess
import time

from django.db import transaction

from vesper.django.app.models import Clip, Job, RecordingChannel
from vesper.util.logging_utils import append_stack_trace
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.text_utils as text_utils
import vesper.util.signal_utils as signal_utils
import vesper.util.time_utils as time_utils


# These are dictated by the Old Bird detector programs.
_INPUT_DIR_PATH = r'C:\My Recordings'
_OUTPUT_DIR_PATH = r'C:\temp\calls'
_STOP_FILE_PATH = r'C:\stop.txt'
_INPUT_FILE_PATH = os.path.join(_INPUT_DIR_PATH, 'Soundfile.wav')
_INPUT_SAMPLE_RATE = 22050

_CLIP_FILE_NAME_PATTERN_FORMAT = r'^{}_\d\d\d\.\d\d\.\d\d_\d\d\.wav$'
"""
Format for creating clip file name regular expression that includes a
particular detector name.
"""

_MIN_CLIP_FILE_PROCESSING_DELAY = 5
"""
The minimum number of seconds that must have elapsed since a clip file
created by an Old Bird detector program was last modified before the
detector monitor will attempt to process it. We impose this wait because
we have found that if we don't, the detector monitor will sometimes try
to process a clip file before the detector program has finished writing
it, resulting in an error. An example of the error message logged by the
detector monitor when this happens is:

    2016-09-13 09:17:44,832 ERROR    Could not read .wav file
        "C:\temp\calls\Tseep_000.02.10_00.wav". Error message was:
        total size of new array must be unchanged
        
The above error message was logged when the minimum processing delay was
set to one second, so I increased it to five seconds. This will not
entirely eliminate the chance that an error will occur, but it should
reduce it substantially.
"""


# TODO: Look into the following error, which occurred while running
# Tseep and Thrush detectors simultaneously:
#
#     2016-09-15 11:15:30,100 ERROR    Attempt to create clip from file
#         "C:\temp\calls\Tseep_002.48.16_00.wav" failed with message:
#         database is locked. File will be ignored.
#
# The database in question was an SQLite database. Do we need to synchronize
# access to the database from different detector monitors? From different
# job processes? If so, maybe it's time to switch to PostgreSQL.


# TODO: Establish conventions for status reporting and error handling for
# commands, and implement here.


class OldBirdDetectorRunner:
    
    """
    Runs the Old Bird Tseep and/or Thrush detectors on archived recordings.
    
    The `run_detectors` method of this class runs the Old Bird Tseep
    and/or Thrush detectors on a single channel of a single recording
    file. The method can only run on Windows, since the Old Bird detectors
    are Windows programs.
    
    Each of the Old Bird detector programs runs in its own process.
    For each running detector program, a *detector monitor* runs on its
    own thread in the main job process, monitoring the status of the
    detector and archiving clips according to the clip files it creates.
    
    Note that due to a limitation of the Old Bird detector programs, all
    detector programs that run simultaneously must run on the same recording
    file and channel. We do not attempt to enforce this, however. The user
    must refrain from running more than one detection job simultaneously.
    """
    
    
    def __init__(self, job_info):
        self._job_info = job_info
        self._logger = logging.getLogger()
        
        
    def run_detectors(self, detectors, recording_file, channel_num):
        
        """
        Runs the specified detectors on one channel of one recording file.
        
        The `detectors` and `recording_file` arguments are Django
        `Processor` and `RecordingFile` model instances. The detectors
        that are run are the Old Bird Tseep-x and/or Thrush-x Windows
        executables, and each detector runs in its own process. Each
        detector process is started by a *detector monitor* that runs
        on its own thread in the same process as the `run_detectors`
        method. After starting its detector, a detector monitor checks
        periodically for clip files output by the detector, creates
        a clip in the archive for each file found, and then deletes
        the file. The detector monitor also reads the detector's log
        file periodically, and terminates the detector process when
        the log file indicates that detection is complete.
        """
        
        # Copy file channel to monaural file required by Old Bird detectors.
        try:
            self._copy_file_channel(recording_file, channel_num)
        except Exception as e:
            self._logger.error(
                'File channel copy failed with message: {}'.format(str(e)))
            return
        
        self._run_detectors_aux(detectors, recording_file, channel_num)
        
        
    def _copy_file_channel(self, recording_file, channel_num):
        
        file_path = recording_file.path
        file_name = os.path.basename(file_path)
        
        self._logger.info((
            'Copying input file "{}" channel {} to "{}"...').format(
                file_name, channel_num, _INPUT_FILE_PATH))
        
        start_time = time.time()
        
        audio_file_utils.copy_wave_file_channel(
            file_path, channel_num, _INPUT_FILE_PATH)
    
        processing_time = time.time() - start_time
        
        self._log_performance(
            'Copied', recording_file.duration, processing_time)
        
        
    def _log_performance(self, prefix, file_duration, processing_time):
        
        format_ = text_utils.format_number
        
        dur = format_(file_duration)
        time = format_(processing_time)
        
        message = '{} {}-second file in {} seconds'.format(prefix, dur, time)
        
        if processing_time != 0:
            speedup = format_(file_duration / processing_time)
            message += ', {} times faster than real time.'.format(speedup)
        else:
            message += '.'
            
        self._logger.info(message)


    def _run_detectors_aux(self, detectors, recording_file, channel_num):

        self._logger.info(
            'Running detectors on file "{}"...'.format(_INPUT_FILE_PATH))
        
        start_time = time.time()
        
        # TODO: Have detector monitors tell us whether or not detection
        # completes normally. For each detector, log whether or not it
        # completed, how many clips it created, how many of those were
        # not archived due to the various possible errors, etc.
        
        monitors = [
            self._start_detector(d, recording_file, channel_num)
            for d in detectors]
        
        self._join_monitors(monitors)

        processing_time = time.time() - start_time
        
        self._log_performance(
            'Detection ran on', recording_file.duration, processing_time)


    def _start_detector(self, detector, recording_file, channel_num):
        
        name = detector.name.split()[-1]
        
        self._logger.info('Starting {} detector...'.format(name))
        
        monitor = _DetectorMonitor(
            name, detector, recording_file, channel_num, self._job_info)
        monitor.start()
        
        return monitor
    
    
    def _join_monitors(self, monitors):
        for monitor in monitors:
            monitor.join()
            
            
class _DetectorMonitor(Thread):
    
    """
    Thread that starts an Old Bird detector process and then monitors
    it, archiving the clips that it creates.
    """
    
    
    def __init__(self, name, detector, recording_file, channel_num, job_info):
        
        super().__init__(name=name)
        
        self._detector = detector
        self._recording_file = recording_file
        self._job_info = job_info
        
        self._recording = recording_file.recording
        self._recording_channel = RecordingChannel.objects.get(
            recording=self._recording, channel_num=channel_num)
        self._mic_output = self._recording_channel.mic_output
        self._sample_rate = recording_file.sample_rate

        self._job = Job.objects.get(id=self._job_info.job_id)
        
        self._executable_name = _get_detector_executable_name(name)
        self._detector_process = None
        
        self._detector_log_path = _get_detector_log_path(name)
        
        pattern = _CLIP_FILE_NAME_PATTERN_FORMAT.format(name)
        self._clip_file_name_re = re.compile(pattern)
        
        
    @property
    def _logger(self):
        return logging.getLogger()
    
    
    def run(self):
        
        try:
            self._prepare_output_dir()
            
        except Exception:
            self._logger.error(append_stack_trace((
                'Preparation of {} detector output directory raised '
                'exception. Detector will not be started.').format(self.name)))
            return
        
        try:
            # Start Old Bird detector executable.
            self._detector_process = subprocess.Popen(
                [self._executable_name], stderr=subprocess.PIPE)
            
        except Exception:
            self._logger.error(append_stack_trace(
                'Attempt to start {} detector raised exception.'.format(
                    self.name)))
            return
            
        try:
            
            while True:
                
                if self._detector_process.poll() is not None:
                    # detector process ended on its own, so there
                    # must have been an error
                    
                    message = self._detector_process.stderr.read()
                    self._logger.error(
                        '{} detector quit with error message: {}'.format(
                            self.name, message.strip()))
                    return
                
                elif self._job_info.stop_requested:
                    # somebody has asked us to stop
                    
                    self._logger.info(
                        'Terminating {} detector in response to stop '
                        'request...')
                    self._detector_process.terminate()
                    return
                
                elif self._is_input_file_exhausted():
                    # detector process finished processing an input file
                    
                    self._logger.info((
                        'Terminating {} detector since detector log indicates '
                        'that sound file processing is complete...').format(
                            self.name))
                    self._detector_process.terminate()
                    break
                    
                else:
                    # detection continues
                    
                    time.sleep(_MIN_CLIP_FILE_PROCESSING_DELAY)
                    self._process_detected_clips(
                        _MIN_CLIP_FILE_PROCESSING_DELAY)
        
        except Exception:
            self._detector_process.terminate()
            self._logger.error(append_stack_trace((
                '{} detector monitor raised exception. Detector has been '
                'terminated.').format(self.name)))
            return
            
        try:
            # If we get here, detection completed normally. Process all
            # remaining clips.
            self._process_detected_clips()
            
        except Exception:
            self._logger.error(append_stack_trace((
                '{} detector monitor raised exception. Detector was already '
                'terminated.').format(self.name)))
    
    
    def _prepare_output_dir(self):
        
        name = self.name
        
        self._logger.info(
            'Clearing {} files from output directory "{}"...'.format(
                name, _OUTPUT_DIR_PATH))
    
        log_path = self._detector_log_path
        os_utils.delete_file(log_path)
        
        pattern = _CLIP_FILE_NAME_PATTERN_FORMAT.format(name)
        os_utils.delete_files(_OUTPUT_DIR_PATH, pattern)
        
        self._logger.info(
            'Creating empty detector log file "{}"...'.format(log_path))
        os_utils.create_file(log_path)


    def _is_input_file_exhausted(self):
        
        contents = os_utils.read_file(self._detector_log_path)
        lines = [line.strip() for line in contents.split('\n')]
        lines = [line for line in lines if line != '']
        nums = [line.split()[-1] for line in lines]
        
        if len(nums) < 2:
            return False
        
        else:
            self._logger.debug(
                '{} detector log times {} {}'.format(
                    self.name, nums[-2], nums[-1]))
            return nums[-2] == nums[-1]
        
        
    def _process_detected_clips(self, min_delay=0):

        file_paths = os_utils.list_files(
            _OUTPUT_DIR_PATH, self._clip_file_name_re)
        
        # Sort file paths in order of detection time.
        file_paths.sort()
        
        for file_path in file_paths:
            
            # We've had problems attempting to read sound files before
            # the Old Bird detector has finished writing them, so we
            # do not attempt to read a file if it was last modified
            # within a certain number of seconds of the current time.
            mod_time = os.path.getmtime(file_path)
            if time.time() - mod_time < min_delay:
                break
            
            # Get clip start time relative to recording file start.
            file_name = os.path.basename(file_path)
            try:
                _, start_delta = _parse_clip_file_name(file_name)
            except ValueError as e:
                self._logger.error((
                    'Could not parse clip file name at "{}". Error message '
                    'was: {}. File will be ignored.').format(file_path, str(e)))
                continue
            
            # TODO: Find clip start index in recording, and use that
            # to archive clip rather than `start_delta`.
            
            # Get clip length from clip file
            try:
                length = audio_file_utils.get_wave_file_info(file_path).length
            except Exception as e:
                self._logger.error((
                    'Could not get information for .wav file "{}". Error '
                    'message was: {}. File will be ignored.').format(
                        file_path, str(e)))
                continue
            
            if self._archive_clip(file_path, start_delta, length):
                self._delete_file(file_path)

            
            
    def _archive_clip(self, file_path, start_delta, length):
        
        if length == 0:
            self._logger.error(
                'Clip file "{}" has zero length and will be ignored.'.format(
                    file_path))
            return False
        
        station = self._recording.station
        
        # TODO: Find exact clip start index in input file.
        start_index = None
        
        # Get clip start time as a `datetime`.
        file_start_index = self._recording_file.start_index
        file_start_seconds = file_start_index / self._sample_rate
        file_start_delta = datetime.timedelta(seconds=file_start_seconds)
        file_start_time = self._recording.start_time + file_start_delta
        start_time = file_start_time + start_delta
        
        end_time = signal_utils.get_end_time(
            start_time, length, self._sample_rate)
        
        creation_time = time_utils.get_utc_now()
        
        try:
            
            with transaction.atomic():
                
                clip = Clip(
                    recording_channel=self._recording_channel,
                    station=station,
                    mic_output=self._mic_output,
                    start_index=start_index,
                    length=length,
                    start_time=start_time,
                    end_time=end_time,
                    date=station.get_night(start_time),
                    creation_time=creation_time,
                    creating_user=None,
                    creating_job=self._job,
                    creating_processor=self._detector
                )
                
                # We must save the clip before getting its wave file path since
                # the path depends on the clip's ID, which not created until the
                # clip is saved.
                clip.save()
                
                if start_index is None:
                    # need to copy clip file
                    
                    self._copy_clip_sound_file(file_path, clip)
                    
        except Exception as e:
            self._logger.error((
                'Attempt to create clip from file "{}" failed with message: '
                '{}. File will be ignored.').format(
                    file_path, str(e)))
            return False
        
        else:
            self._logger.info('Archived {} clip {}.'.format(self.name, clip))
            return True


    def _copy_clip_sound_file(self, file_path, clip):
        
        with open(file_path, 'rb') as file_:
            contents = file_.read()
             
        # Create clip directory if needed.
        dir_path = os.path.dirname(clip.wav_file_path)
        os_utils.create_directory(dir_path)
        
        with open(clip.wav_file_path, 'wb') as file_:
            file_.write(contents)


    def _delete_file(self, file_path):
        try:
            os_utils.delete_file(file_path)
        except Exception as e:
            self._logger.error(str(e))


def _get_detector_executable_name(detector_name):
    return '{}-x.exe'.format(detector_name)


def _get_detector_log_path(detector_name):
    file_name = 'Log{}.txt'.format(detector_name)
    return os.path.join(_OUTPUT_DIR_PATH, file_name)


_CLIP_FILE_NAME_RE = re.compile(
    r'^([a-zA-Z]+)_(\d\d\d)\.(\d\d)\.(\d\d)_(\d\d)\.wav+$')
"""Regular expression for matching a clip file name for any detector."""


def _parse_clip_file_name(file_name):
    
    m = _CLIP_FILE_NAME_RE.match(file_name)
    
    if m is None:
        _raise_value_error(file_name)
        
    else:
        
        (detector_name, hhh, mm, ss, nn) = m.groups()
        
        hours = int(hhh)
        minutes = int(mm)
        seconds = int(ss)
        num = int(nn)
    
        _check(file_name, 'minutes', time_utils.check_minutes, minutes)
        _check(file_name, 'seconds', time_utils.check_seconds, seconds)
        _check_num(num, file_name)
            
        elapsed_time = datetime.timedelta(
            hours=hours, minutes=minutes, seconds=seconds,
            microseconds=num * 100000)
        
        return (detector_name, elapsed_time)


def _raise_value_error(file_name, message=None):
    
    if message is None:
        message = 'Bad clip file name "{}".'.format(file_name)
    else:
        message = '{} in clip file name "{}".'.format(message, file_name)
        
    raise ValueError(message)


def _check(file_name, part_name, check, n, *args):
    try:
        check(n, *args)
    except ValueError:
        _raise_value_error(file_name, 'Bad {} "{}"'.format(part_name, n))


def _check_num(num, file_name):
    if num > 9:
        _raise_value_error(
            file_name, 'Clip number {} is too high.'.format(num))
