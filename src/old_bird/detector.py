"""Module containing `Detector` class."""


from threading import Event, Thread
import logging
import os
import re
import subprocess
import time

import pytz

from old_bird.file_name_utils import \
    parse_elapsed_time_clip_file_name as _parse_clip_file_name
from vesper.exception.command_exceptions import CommandFormatError
from vesper.util.audio_file_utils import read_wave_file as _read_wave_file
from vesper.util.bunch import Bunch
from vesper.util.task_serializer import TaskSerializer
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.time_utils as time_utils
import vesper.util.vcl_utils as vcl_utils


'''
To run Tseep-x on a sound file one should:

1. Create the directory `C:\My Recordings` if it does not already exist.

2. Copy the file that the detector is to be run on to
   `C:\My Recordings\Soundfile.wav`.

3. If the directory `C:\temp\calls` exists, delete its contents.
   Otherwise create the directory.

4. Delete the file `C:\stop.txt` if it exists.

5. Start Tseep-x.exe.

6. Check the file `C:\temp\calls\LogTseep.txt` periodically to see
   if the energy measurements of the last n lines are identical.
   When they are, create the file `C:\stop.txt` to stop Tseep-x.exe.
'''


'''
In writing code that interacts with the Windows file system (more
specifically, the file system on my Windows 8.1 Parallels VM), I have
run into some permissions issues.

1. While I can delete a file from the `C:\My Recordings` directory or copy
a file to it without issue, attempting to create a symbolic link within
the directory fails due to insufficient privileges. This is unfortunate
since creating a symbolic link to a large input file is much faster than
copying it. Once we have something working that doesn't require
administrator privileges we might investigate running the script with
administrator privileges so it can create links, or changing permissions
so that the user running the script can create symbolic links. The code
to create a symbolic link is:

    win32file.CreateSymbolicLink(_INPUT_FILE_PATH, input_file_path)
    
2. Attempts to either delete or rename `C:\Stop.txt` also fail due to
insufficient privileges. Since the file stops the detector from running,
we ask the user to delete it if it exists.
'''


_DETECTOR_NAME_TSEEP = 'Tseep'
_DETECTOR_NAME_THRUSH = 'Thrush'
_DETECTOR_NAME_DICK = 'Dick'
_DETECTOR_NAMES = frozenset((
    _DETECTOR_NAME_TSEEP, _DETECTOR_NAME_THRUSH, _DETECTOR_NAME_DICK))

_INPUT_MODE_MICROPHONE = 'Mic'
_INPUT_MODE_LINE = 'Line'
_INPUT_MODE_FILE = 'File'
_INPUT_MODES = frozenset((
    _INPUT_MODE_MICROPHONE, _INPUT_MODE_LINE, _INPUT_MODE_FILE))
_INPUT_MODE_SUFFIXES = {
    _INPUT_MODE_MICROPHONE: 'r',
    _INPUT_MODE_LINE: 'o',
    _INPUT_MODE_FILE: 'x'
}

# These are dictated by the Old Bird detector programs.
# TODO: Use raw strings for Windows paths.
_INPUT_DIR_PATH = 'C:\\My Recordings'
_OUTPUT_DIR_PATH = 'C:\\temp\\calls'
_STOP_FILE_PATH = 'C:\\stop.txt'
_INPUT_FILE_PATH = os.path.join(_INPUT_DIR_PATH, 'Soundfile.wav')
_CLIP_FILE_NAME_PATTERN = r'^{:s}_\d\d\d\.\d\d\.\d\d_\d\d\.wav$'

_CLIP_FILE_PROCESSING_DELAY = 1

# TODO: This path should not be hard-coded. Perhaps there should be a
# default location (e.g. the user's `Desktop` directory, otherwise the
# `Old Bird` subdirectory of `%ProgramFiles(x86)%` if it exists,
# otherwise of `%ProgramFiles%`, otherwise `None`) with the option to
# override on the command line. Observe `%OLD_BIRD_HOME%`? Or maybe
# we should just insist that the detector be on the user's path.
_DETECTOR_DIR_PATH = 'C:\\Program Files (x86)\\Old Bird'


# TODO: This detector should only be available on Windows, so we really
# need plug-ins! For the time being, if present on other platforms it
# should import but decline to run.


class Detector(object):
    
    
    def __init__(self, positional_args, keyword_args):
        
        if len(positional_args) != 0:
            s = 's' if len(positional_args) > 1 else ''
            args = ' '.join(positional_args)
            message = 'Extra positional argument{:s}: {:s}'.format(s, args)
            raise CommandFormatError(message)
        
        self._detector_names = _get_detector_name(keyword_args)
        self._input_mode = _get_input_mode(keyword_args)
        self._input_paths = _get_input_paths(keyword_args)
        
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        self._archive_task_serializer = TaskSerializer()
        
        # Make sure we can open archive.
        archive = vcl_utils.open_archive(self._archive_dir_path)
        archive.close()
        
                
    def detect(self):
        
        # TODO: Develop Vesper command error handling policy and implement
        # it for this command. As of this writing `os_utils` functions
        # can raise exceptions that are not handled, `AssertionError`
        # exceptions are raised that are not handled, and there may be
        # additional, similar problems.
        
        _check_detection_setup()
        
        if self._input_mode == _INPUT_MODE_FILE:
            
            self._archive = self._archive_task_serializer.run(
                vcl_utils.open_archive, self._archive_dir_path)
#            self._archive = vcl_utils.open_archive(self._archive_dir_path)
            
            try:
                self._detect_on_dirs_and_files()
            finally:
                self._archive_task_serializer.run(self._archive.close)
#                self._archive.close()
        
        
    def _detect_on_dirs_and_files(self):
        
        for path in self._input_paths:
            
            if not os.path.exists(path):
                message = (
                    'Input path "{:s}" does not exist and will be '
                    'ignored.').format(path)
                logging.info(message)
                    
            else:
                # path exists
                
                if os.path.isdir(path):
                    self._detect_on_dir(path)
                    
                else:
                    self._detect_on_file(path)
                    
                    
    def _detect_on_dir(self, dir_path):
                    
        for _, subdir_names, file_names in os.walk(dir_path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                if _is_audio_file(file_path):
                    self._detect_on_file(file_path)
                
            # stop walk from visiting subdirectories
            del subdir_names[:]
            
            
    def _detect_on_file(self, file_path):
        
        s = 's' if len(self._detector_names) > 1 else ''
        logging.info(
            'Running detector{:s} on file "{:s}"...'.format(s, file_path))
        
        try:
            (self._station_name, self._monitoring_start_time,
             self._num_samples) = \
                _get_input_file_info(file_path)
                
        except ValueError as e:
            logging.error((
                'Could not get information for file "{:s}". '
                'Error message was: {:s}').format(file_path, str(e)))
            return
            
#         logging.info(
#             'station {:s} start time {:s} num samples {:d}'.format(
#                 self._station_name, str(self._monitoring_start_time),
#                 self._num_samples))
        
        try:
            self._copy_input_file(file_path)
            
        except OSError as e:
            logging.error(str(e))
        
        else:
            detectors = self._start_detectors()
            self._wait_for_detectors(detectors)
            
            
    def _copy_input_file(self, file_path):
        
        file_name = os.path.basename(file_path)
        logging.info(
            'Copying input file "{:s}" to "{:s}"...'.format(
                file_name, _INPUT_FILE_PATH))
        os_utils.copy_file(file_path, _INPUT_FILE_PATH)
        
        
    def _start_detectors(self):
        
        detectors = []
        
        for name in self._detector_names:
            
            detector = _Detector(
                name, self._input_mode, self._handle_detection)
            
            logging.info('Starting {:s} detector...'.format(name))
            
            try:
                detector.start()
                
            except OSError as e:
                logging.error((
                    'Could not start "{:s}" detector. Error message '
                    'was: {:s}').format(name, str(e)))
                
            else:
                detectors.append(detector)
                
        return detectors
    
    
    def _handle_detection(self, clip):
        file_name = os.path.basename(clip.file_path)
        start_time = self._monitoring_start_time + clip.start_time
        logging.info(
            'Archiving {:s} {:s} {:s} {:s}...'.format(
                file_name, self._station_name, clip.detector_name,
                str(start_time)))
        try:
            self._archive_task_serializer.run(
                self._archive.add_clip, self._station_name,
                clip.detector_name, start_time, clip)
        except ValueError as e:
            logging.error(
                'Clip archival failed with message: {:s}'.format(str(e)))
        

    def _wait_for_detectors(self, detectors):
        for detector in detectors:
            detector.join()
            logging.info(
                '{:s} detector is no longer running.'.format(detector.name))
    
    
def _check_detection_setup():
    _assert_dir(_INPUT_DIR_PATH)
    _assert_dir(_OUTPUT_DIR_PATH)
    _assert_no_file(_STOP_FILE_PATH)
    
    
def _assert_dir(path):
    try:
        os_utils.assert_directory(path)
    except AssertionError:
        message = (
            'The directory "{:s}" does not exist. Please create it '
            'and try again.').format(path)
        raise AssertionError(message)


def _assert_no_file(path):
    if os.path.exists(path):
        message = (
            'The file "{:s}" will interfere with detection. '
            'Please delete it and try again.').format(path)
        raise AssertionError(message)
    

def _configure_file_detector_input(input_file_path):
    input_file_name = os.path.basename(input_file_path)
    logging.info(
        'Copying input file "{:s}" to "{:s}"...'.format(
            input_file_name, _INPUT_FILE_PATH))
    os_utils.copy_file(input_file_path, _INPUT_FILE_PATH)


def _get_detector_log_path(detector_name):
    file_name = 'Log{:s}.txt'.format(detector_name)
    return os.path.join(_OUTPUT_DIR_PATH, file_name)


def _get_detector_executable_path(detector_name, input_mode):
    suffix = _INPUT_MODE_SUFFIXES[input_mode]
    file_name = '{:s}-{:s}.exe'.format(detector_name, suffix)
    return os.path.join(_DETECTOR_DIR_PATH, file_name)


def _get_detector_name(keyword_args):
    
    try:
        names = keyword_args['detectors']
    except KeyError:
        message = 'Missing required "--detectors" argument.'
        raise CommandFormatError(message)
    
    for name in names:
        if name not in _DETECTOR_NAMES:
            message = 'Unrecognized detector "{:s}".'.format(name)
            raise CommandFormatError(message)
        
    return names


def _get_input_mode(keyword_args):
    
    # TODO: Make --input-mode argument optional, and infer its value
    # in some or all cases?
    
    try:
        modes = keyword_args['input-mode']
    except KeyError:
        raise CommandFormatError('Missing required "--input-mode" argument.')
    
    if len(modes) != 1:
        raise CommandFormatError(
            '"--input-mode" argument value must be a single string.')
    
    mode = modes[0]
    
    if mode not in _INPUT_MODES:
        message = 'Unrecognized input mode "{:s}".'.format(mode)
        raise CommandFormatError(message)
        
    # For now we support only file input.
    if mode != _INPUT_MODE_FILE:
        message = (
            'Sorry, but only the "{:s}" input mode is supported at this '
            'time.').format(_INPUT_MODE_FILE)
        raise CommandFormatError(message)
    
    return mode
    
    
def _get_input_paths(keyword_args):
    
    try:
        values = keyword_args['input-paths']
    except KeyError:
        message = 'Missing required "--input-paths" argument.'
        raise CommandFormatError(message)
    
    return values


def _is_audio_file(path):
    return path.endswith('.wav')


# TODO: Add extension point for provision of monitoring info, including
# station name, start time, and duration. We currently assume .wav files
# with names of a certain format, parsed by the `_get_input_file_info`
# function.


_INPUT_FILE_NAME_RE = \
    re.compile(r'^(.+)_(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d).wav$')


def _get_input_file_info(file_path):
    
    name = os.path.basename(file_path)

    m = _INPUT_FILE_NAME_RE.match(name)
    
    if m is None:
        raise ValueError((
            'File name is not of the form '
            '<station name>_<yyyymmdd>_<hhmmss>.wav'))
        
    station, year, month, day, hour, minute, second = m.groups()
    start_time = time_utils.parse_date_time(
        year, month, day, hour, minute, second)
    
    # Convert naive monitoring start time to UTC. We assume that the
    # local time zone is US/Mountain, that the naive start time observes
    # DST, and that it will never be ambiguous or nonexistent (i.e. we
    # do not worry about the `is_dst` argument to `mountain.localize`).
    # If we do supply an ambiguous or nonexistent time to
    # `mountain.localize` it will raise an exception. See the
    # "Problems with Localtime" section of the `pytz` documentation at
    # http://pytz.sourceforge.net for more.
    mountain = pytz.timezone('US/Mountain')
    start_time = mountain.localize(start_time)
    start_time = start_time.astimezone(pytz.utc)
    
    (num_channels, sample_size, frame_rate, num_frames, compression_type) = \
        audio_file_utils.get_wave_file_info(file_path)
    
    if num_channels != 1:
        raise ValueError(
            'File has {:d} channels, but only one channel is currently '
            ' supported.'.format(num_channels))
        
    if sample_size != 16:
        raise ValueError((
            'File has {:d}-bit samples, but only 16-bit samples are '
            'currently supported.').format(sample_size))
        
    if frame_rate != 22050:
        raise ValueError((
            'File has a sample rate of {:g} Hz, but only a sample rate '
            ' of 22050 Hz is currently supported.').format(frame_rate))
        
    if compression_type != 'NONE':
        raise ValueError((
            'File has a compression type of "{:s}", but only a compression '
            'type of "NONE" is curently supported.').format(compression_type))

    return (station, start_time, num_frames)
            
        
class _Detector(Thread):
    
    
    def __init__(self, name, input_mode, detection_handler):
        
        super(_Detector, self).__init__(name=name)
        
        self.name = name
        self.input_mode = input_mode
        self.detection_handler = detection_handler
        
        self._executable_path = _get_detector_executable_path(name, input_mode)
        self._detector_process = None
        self._stop_event = Event()
        
        self._log_path = _get_detector_log_path(name)
        
        pattern = _CLIP_FILE_NAME_PATTERN.format(name)
        self._clip_file_name_re = re.compile(pattern)
        
        
    def run(self):
        
        # TODO: Do we need to ensure that all output directory clearing
        # and all clip processing happens on a single thread? Both involve
        # walks and file deletion, and I don't know whether or not it
        # would be safe for those operations to happen on different
        # `_Detector` threads.
        
        self._prepare_output_dir()
        
        # Start Old Bird detector executable.
        self._detector_process = subprocess.Popen(
            [self._executable_path], stderr=subprocess.PIPE)
            
        while True:
            
            if self._detector_process.poll() is not None:
                # detector process ended on its own, so there
                # must have been an error
                
                message = self._detector_process.stderr.read()
                logging.error(
                    '{:s} detector quit with error message: {:s}'.format(
                        self.name, message.strip()))
                break
            
            elif self._stop_event.is_set():
                # somebody told us to stop
                
                logging.info(
                    'Terminating {:s} detector in response to stop command...')
                self._detector_process.terminate()
                break
            
            elif self.input_mode == _INPUT_MODE_FILE and \
                 self._is_input_file_exhausted():
                # detector process finished processing an input file
                
                logging.info((
                    'Terminating {:s} detector since log indicates it has '
                    'finished processing sound file...').format(self.name))
                self._detector_process.terminate()
                break
                
            else:
                # detection continues
                
                time.sleep(1)
                self._process_detected_clips(_CLIP_FILE_PROCESSING_DELAY)
            
        # At this point the detector process is no longer running.
        # We process any remaining clips to ensure that we do not
        # miss any.
        self._process_detected_clips()
    
    
    def _prepare_output_dir(self):
        
        name = self.name
        
        logging.info(
            'Clearing "{:s}" files from output directory "{:s}"...'.format(
                name, _OUTPUT_DIR_PATH))
    
        log_path = _get_detector_log_path(name)
        os_utils.delete_file(log_path)
        
        pattern = _CLIP_FILE_NAME_PATTERN.format(name)
        os_utils.delete_files(_OUTPUT_DIR_PATH, pattern)
        
        logging.info('Creating empty log file "{:s}"...'.format(log_path))
        os_utils.create_file(log_path)


    def _is_input_file_exhausted(self):
        
        try:
            with open(self._log_path) as file_:
                contents = file_.read()
        except Exception:
            logging.error(
                'Could not read detector log file "{:s}".'.format(
                    self._log_path))
            return False
        
        lines = [line.strip() for line in contents.split('\n')]
        lines = [line for line in lines if line != '']
        nums = [line.split()[-1] for line in lines]
        
        if len(nums) < 2:
            return False
        
        else:
            logging.debug(
                '{:s} detector log times {:s} {:s}'.format(
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
            
            start_time = self._get_clip_start_time(file_path)
                
            if start_time is not None:
                
                samples, sample_rate = self._read_wave_file(file_path)
                
                if samples is not None:
                
                    clip = Bunch(
                        detector_name=self.name,
                        start_time=start_time,
                        samples=samples,
                        sample_rate=sample_rate,
                        file_path=file_path)
                
                    self.detection_handler(clip)
                    
                    self._delete_file(file_path)
            
            
    def _get_clip_start_time(self, file_path):
        
        file_name = os.path.basename(file_path)
        
        try:
            _, start_time = _parse_clip_file_name(file_name)
            
        except ValueError, e:
            logging.error((
                'Could not parse clip file name at "{:s}". Error '
                'message was: {:s}').format(file_path, str(e)))
            return None
        
        return start_time
            

    def _read_wave_file(self, file_path):
        
        try:
            samples, frame_rate = _read_wave_file(file_path)
            return (samples[0], frame_rate)
        
        except Exception as e:
            logging.error((
                'Could not read .wav file "{:s}". Error message was: '
                '{:s}').format(file_path, str(e)))
            return (None, None)
    
    
    def _delete_file(self, file_path):
        try:
            os_utils.delete_file(file_path)
        except Exception as e:
            logging.error(str(e))
                    

    def stop(self):
        self._stop_event.set()
        
    
'''
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode File --input-paths ...
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode Live
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode Playback --start-time "2014-08-26 07:25:00 MDT"
'''
        
'''
command name: detect
positional arguments:
    - name: detector
      type: string
'''

'''
positional arguments:
keyword arguments:
    detectors:
        type: string list
        values: [Tseep Thrush]
    input-mode:
        type: string
        values: [Live Playback File]
    start-time:
        type: date-time
        context: input-mode == Playback
    input-paths:
        type: string list
        context: input-mode == File
'''
        
        
# class _StringParser(object):
#     
#     def __init__(self, config):
#         self._config = config
#         
#     def parse_value(self, value):
#         pass
#         
#         
# _argument_classes = {
#     'String': _StringParser,
#     'Integer': _IntegerParser,
#     'Float': _FloatParser,
#     'DateTime': _DateTimeParser
# }
# 
# 
# def _get_keyword_arg(
#         args, name, value_type, values=None, default=None, required=True):
#     
#     try:
#         value = args[name]
#         
#     except KeyError:
#         if required:
#             message = 'Missing required keyword argument "{:s}".'.format(name)
#             raise CommandFormatError(message)
#         else:
#             return default
#         
#     
#     if values is not None and value not in values:
#         message = 'Illegal value "{:s}" for keyword argument'
#         raise CommandFormatError(message)
    