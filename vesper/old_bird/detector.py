"""Module containing `Detector` class."""


from threading import Event, Thread
import logging
import math
import os
import re
import subprocess
import time

import yaml

from vesper.archive.recording import Recording
from vesper.archive.station import Station
from vesper.mpg_ranch.song_meter_audio_file_parser \
    import SongMeterAudioFileParser as MpgRanchSongMeterAudioFileParser
from vesper.old_bird.file_name_utils \
    import parse_elapsed_time_clip_file_name as _parse_clip_file_name
from vesper.util.audio_file_utils import read_wave_file as _read_wave_file
from vesper.util.bunch import Bunch
from vesper.util.task_serializer import TaskSerializer
from vesper.vcl.command import CommandExecutionError, CommandSyntaxError
import vesper.archive.recording_utils as recording_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.os_utils as os_utils
import vesper.util.text_utils as text_utils
import vesper.util.time_utils as time_utils
import vesper.vcl.vcl_utils as vcl_utils


# TODO: Refactor this module. It contains a jumble of generic detector
# functionality, Old-Bird-detector-specific functionality, and
# MPG-Ranch-specific functionality that needs to be untangled.

# TODO: Add support for input from audio devices.


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
_INPUT_DIR_PATH = r'C:\My Recordings'
_OUTPUT_DIR_PATH = r'C:\temp\calls'
_STOP_FILE_PATH = r'C:\stop.txt'
_INPUT_FILE_PATH = os.path.join(_INPUT_DIR_PATH, 'Soundfile.wav')
_INPUT_SAMPLE_RATE = 22050
_CLIP_FILE_NAME_PATTERN = r'^{:s}_\d\d\d\.\d\d\.\d\d_\d\d\.wav$'

_CLIP_FILE_PROCESSING_DELAY = 1

# TODO: This path should not be hard-coded. Perhaps there should be a
# default location (e.g. the user's `Desktop` directory, otherwise the
# `Old Bird` subdirectory of `%ProgramFiles(x86)%` if it exists,
# otherwise of `%ProgramFiles%`, otherwise `None`) with the option to
# override on the command line. Observe `%OLD_BIRD_HOME%`? Or maybe
# we should just insist that the detector be on the user's path.
_DETECTOR_DIR_PATH = r'C:\Program Files (x86)\Old Bird'


# TODO: This detector should only be available on Windows, so we really
# need plug-ins! For the time being, if present on other platforms it
# should import but decline to run.


'''
To use default detection handler, which writes detections to an archive:

    vcl detect "Old Bird" --detectors Tseep Thrush --input-mode File
        --input-paths /Users/Harold/Desktop/NFC [--archive <archive-path>]
    
To use MPG Ranch Renamer detection handler, which moves and renames
detection sound files:

    vcl detect "Old Bird" --detectors Tseep Thrush --input-mode File
        --input-paths /Users/Harold/Desktop/NFC
        --detection-handler "MPG Ranch Renamer"
        
These commands work fine when there is only a single detection handler.
We would have to do something different if we wanted to support multiple
detection handlers, perhaps by allowing a handler configuration to be
specified via a YAML file (or even a command line argument that includes
a YAML string).
'''


# TODO: Certain information, such as the start time of a recording,
# is needed by a detector for any audio input source. Factor out the
# gathering of this information, adding extension types (e.g. perhaps
# for a sound file name parser) as needed.

# TODO: Split detection handling out into extensions. Note that the need
# for detection handling is not specific to the Old Bird detector (every
# detector takes as input a continuous stream of audio and outputs
# discrete detections), and the extensions should reflect this.


class DetectionHandlerError(Exception):
    pass


class DetectionHandler(object):
    
    
    def __init__(self, keyword_args):
        
        super(DetectionHandler, self).__init__()
        
        # TODO: Create an input file parser extension point and repackage
        # the file parser as an extension that is specified and configured
        # by VCL command arguments. Parsing file names and getting audio
        # file metadata from within the file are concerns that I worry
        # are not currently as separate as I suspect they should be.
        # Think about this.
        self._input_file_parser = MpgRanchSongMeterAudioFileParser()
        
        self._success = True
    
    
    def on_detection_start(self):
        pass
    
    
    def get_recordings(self, input_paths):
        
        file_paths = self._get_input_file_paths(input_paths)
        recordings = self._create_recordings(file_paths)
        recordings = recording_utils.merge_recordings(recordings)
        return (recordings, self._success)
        
        
    def _get_input_file_paths(self, input_paths):
        
        file_paths = []
        
        for path in input_paths:
            
            if not os.path.exists(path):
                self._handle_nonexistent_path(path)
                    
            else:
                # path exists
                
                if os.path.isdir(path):
                    file_paths += self._get_input_file_paths_in_dir(path)
                    
                else:
                    file_paths.append(path)
                    
        return file_paths
    
    
    def _handle_nonexistent_path(self, path):
        message = (
            'Input path "{:s}" does not exist and will be '
            'ignored.').format(path)
        logging.error(message)
        self._success = False
        
   
    def _get_input_file_paths_in_dir(self, dir_path):
        
        file_paths = []
        
        for _, subdir_names, file_names in os.walk(dir_path):
            
            for file_name in file_names:
                file_path = os.path.join(dir_path, file_name)
                if self._is_input_file_path(file_path):
                    file_paths.append(file_path)
                
            # stop walk from visiting subdirectories
            del subdir_names[:]
            
        return file_paths
            
            
    def _is_input_file_path(self, path):
        return path.endswith('.wav')


    def _create_recordings(self, file_paths):
        
        recordings = []
        
        for file_path in file_paths:
            
            try:
                channel_recordings = self._create_channel_recordings(file_path)
                
            except ValueError as e:
                logging.error((
                    'Could not parse input path "{}": file will be ignored. '
                    'Error message was: {}').format(file_path, str(e)))
                self._success = False
                
            else:
                recordings += channel_recordings
                
        return recordings
    
    
    def _create_channel_recordings(self, file_path):
        
        info = self._input_file_parser.get_file_info(file_path)
        
        _check_sample_rate(info.sample_rate, file_path)
            
        recordings = []
        
        for channel_num, microphone_name in \
                enumerate(info.channel_microphone_names):
            
            if microphone_name is not None:
                
                station_name = info.station_name + ' ' + microphone_name
                
                # TODO: The following raises a `ValueError` if there
                # is no station with the specified name, for example if
                # the microphone name is unrecognized. Figure out how
                # best to deal with this. It might be better to do so
                # in the file parser rather than here.
                station = self._get_station(station_name)
                
                # Get UTC start time from local start time using station
                # time zone.
                t = info.start_time
                start_time = time_utils.create_utc_datetime(
                    t.year, t.month, t.day, t.hour, t.minute, t.second,
                    time_zone=station.time_zone)
                    
                recording = Recording(
                    station, start_time, info.length, info.sample_rate)
                recording.file_path = file_path
                recording.channel_num = channel_num
                recording.microphone_name = microphone_name
                
                recordings.append(recording)
        
        return recordings

    
    def _get_station(self, station_name):
        raise NotImplementedError()
    
    
    def on_recording_start(self, recording):
        pass
    
    
    def on_subrecording_start(self, subrecording):
        pass
    
    
    def on_detection(self, clip):
        pass
    
    
    def on_subrecording_end(self, subrecording):
        pass
    
    
    def on_recording_end(self, recording):
        pass
    
    
    def on_detection_end(self):
        pass
    
        
class DetectionArchiver(DetectionHandler):
    
    
    def __init__(self, keyword_args):
        super(DetectionArchiver, self).__init__(keyword_args)
        self._archive_dir_path = vcl_utils.get_archive_dir_path(keyword_args)
        
        
    def on_detection_start(self):
        self._archive_task_serializer = TaskSerializer()
        self._archive = self._archive_task_serializer.execute(
            vcl_utils.open_archive, self._archive_dir_path)
    
    
    def _get_station(self, station_name):
        return self._archive_task_serializer.execute(
            self._archive.get_station, station_name)


    def on_recording_start(self, recording):
        
        r = recording
        self._station = r.station
        
        try:
            self._archive_task_serializer.execute(
                self._archive.add_recording, r.station.name, r.start_time,
                r.length, r.sample_rate)
        
        except ValueError as e:
            logging.error(
                'Recording archival failed: {:s}'.format(str(e)))
            self._success = False
        
        
    def on_subrecording_start(self, subrecording):
        self._subrecording_start_time = subrecording.start_time
        
        
    def on_detection(self, clip):
        
        file_name = os.path.basename(clip.file_path)
        start_time = self._subrecording_start_time + clip.start_time
        
        s = start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-5]
        s += ' ' + start_time.strftime('%Z')
        logging.info(
            'Archiving {:s} ({:s} {:s})...'.format(
                file_name, self._station.name, s))
        
        try:
            self._archive_task_serializer.execute(
                self._archive.add_clip, self._station.name,
                clip.detector_name, start_time, clip)
            
        except ValueError as e:
            logging.error(
                'Clip archival failed: {:s}'.format(str(e)))
            self._success = False


    def on_detection_end(self):
        self._archive_task_serializer.execute(self._archive.close)


class DetectionRenamer(DetectionHandler):
    
    """
    Moves and renames detections in accordance with the first steps of the
    MPG Ranch Tseep and Thrush detection workflow.
    """
    
    
    def on_detection_start(self):
        self._station_name_changes = _get_station_name_changes()
        self._stations = {}
        
        
    def _get_station(self, station_name):
        
        try:
            return self._stations[station_name]
        
        except KeyError:
            station = Station(station_name, '', 'US/Mountain')
            self._stations[station_name] = station
            return station


    def on_subrecording_start(self, subrecording):

        station = subrecording.station
        
        # Format station name for directory name.
        name = station.name.lower()
        station_name = self._station_name_changes.get(name, name)
        
        # Format start time for directory name.
        start_time = subrecording.start_time.astimezone(station.time_zone)
        start_time = start_time.strftime('%m%d%y_%H%M%S')
        
        # Format duration for directory name.
        duration = subrecording.length / float(subrecording.sample_rate)
        hours = int(math.floor(duration / 3600))
        duration -= hours * 3600
        minutes = int(math.floor(duration / 60))
        seconds = int(round(duration - minutes * 60))
        duration = '{:02d}{:02d}{:02d}'.format(hours, minutes, seconds)
        
        # Create directory name and path.
        dir_name = station_name + '_' + start_time + '_' + duration
        dir_path = os.path.join(_OUTPUT_DIR_PATH, dir_name)
        
        if os.path.exists(dir_path):
            raise DetectionHandlerError((
                'Detection output directory "{:s}" already exists. Please '
                'delete it and try again.').format(dir_path))
            
        try:
            os_utils.create_directory(dir_path)
        except OSError as e:
            raise DetectionHandlerError((
                'Could not create output directory "{:s}". Error message '
                'was: {:s}').format(dir_path, str(e)))
            
        self._dir_name = dir_name
        self._dir_path = dir_path
        
            
    def on_detection(self, clip):
        
        old_file_name = os.path.basename(clip.file_path)
        new_file_name = self._dir_name + '_' + old_file_name
        new_file_path = os.path.join(self._dir_path, new_file_name)
        
        logging.info(
            'Copying {:s} to {:s}...'.format(old_file_name, new_file_name))

        try:
            os_utils.copy_file(clip.file_path, new_file_path)
        except OSError as e:
            raise DetectionHandlerError(str(e))


def _check_sample_rate(sample_rate, file_path):
    if sample_rate != _INPUT_SAMPLE_RATE:
        raise ValueError((
            'Sample rate is {:g} Hz rather than the required {:d} Hz '
            'for input sound file "{:s}".').format(
                sample_rate, _INPUT_SAMPLE_RATE, file_path))


def _get_station_name_changes():
    
    file_path = os.path.join(_OUTPUT_DIR_PATH, 'StationNameChanges.yaml')
    
    if os.path.exists(file_path):
        
        try:
            text = os_utils.read_file(file_path)
        except OSError:
            raise DetectionHandlerError(
                'Could not read YAML file "{:s}".'.format(file_path))
        
        try:
            changes = yaml.load(text)
        except yaml.parser.ParserError:
            raise DetectionHandlerError(
                'Could not parse YAML file "{:s}".'.format(file_path))
            
        if isinstance(changes, dict):
            return changes
        else:
            raise DetectionHandlerError(
                'Contents of YAML file "{:s}" are not a dictionary.'.format(
                    file_path))
            
    else:
        return {}
                
                
_HELP = '''
<keyword arguments>

Detects nocturnal flight calls (NFCs) using programs from Old Bird, Inc.

NFCs are detected using either or both of the Old Bird Tseep and
Thrush detectors, as specified via the --detectors argument.
Detection is performed on one or more .wav files. By default the
detected calls are added to an archive, but this behavior can be
overridden via the --detection-handler argument.

This detector is only available on Windows computers, and requires
that Old Bird's Tseep-x (see http://oldbird.org/tseep.htm) and/or
Thrush-x (see http://oldbird.org/Thrush.htm) detectors are installed
in the directory "C:\\Program Files (x86)\\Old Bird" (or
"C:\\Program Files\\Old Bird" if you're using an older, 32-bit
version of Windows). Additional requirements for the proper operation
of the Old Bird detectors must also be satisfied. See the above links
for details.

Detection on input from a computer's sound card using the Old Bird
Tseep-o, Tseep-r, Thrush-o, and Thrush-r detectors is not currently
supported, but is planned.
'''.strip()


'''
To use default detection handler, which writes detections to an archive:

    vcl detect "Old Bird"
        --detectors Tseep Thrush
        --input-mode File
        --input-paths /Users/Harold/Desktop/NFC
        [--archive <archive-path>]
    
To use the MPG Ranch Renaming Detection Handler, which moves and renames
detection sound files:

    vcl detect "Old Bird"
        --detectors Tseep Thrush
        --input-mode File
        --input-paths /Users/Harold/Desktop/NFC
        --detection-handler "MPG Ranch Renamer"
        
These commands work fine when there is only a single detection handler.
We would have to do something different if we wanted to support multiple
detection handlers, perhaps by allowing a handler configuration to be
specified via a YAML file (or even a command line argument that includes
a YAML string).
'''


# TODO: Make detection handlers extensions and figure out how to handle
# documentation for them. This is the first command where an extension is
# chosen with a keyword argument rather than a positional argument.

# TODO: "archive" argument should be associated with `DetectionArchiver`
# detection handler. The documentation for that argument should come
# from the handler extension.

# TODO: Provide a means of specifying argument dependencies (e.g.
# --input-paths only makes sense when --input-mode is "File") in
# YAML argument descriptors, and make documentation reflect dependencies.

# TODO: There are both positional and keyword arguments whose values
# are extension names. Can we unify the construction of documentation
# for such arguments?

# TODO: Provide for specification of sets of mutually exclusive arguments.

# TODO: Do away with --input-mode argument and infer input mode from
# other arguments?


_ARGS = r'''

- name: --detectors
  required: true
  value description: Old Bird detector names
  documentation: |
      The Old Bird NFC detectors to run.
      Available detectors:
          Tseep
          Thrush
  
- name: --input-mode
  required: true
  value description: mode
  documentation: |
      The mode of audio input.
      Available modes:
          File
              Input is taken from one or more .wav files specified via the
              --inputs argument.
  
- name: --inputs
  required: true
  value description: file and/or directory paths
  documentation: |
      The audio input files and directories on which to detect.
      Files must be .wav files with a sample rate of 22050 Hz. For each
      directory, all of the .wav files of the directory (but not of any
      subdirectories of the directory) are taken as input.
      Dependency: --input-mode File
  
- name: --detection-handler
  required: false
  value description: name
  documentation: |
      The detection handler with which to process each detection.
      Available handlers:
          Archiver
              Adds each detection to an archive. The archive can be
              specified via the --archive argument.
          MPG Ranch Renamer
              Renames each detection .wav file in accordance with the
              MPG Ranch migration monitoring workflow.
      Default: Archiver
  
- name: --archive
  required: false
  value description: directory path
  documentation: |
      The archive to which to add detections.
      Dependency: --detection-handler Archiver
      Default: The archive of the current directory.
  
'''


class Detector(object):
    
    
    name = 'Old Bird'
    
    
    @staticmethod
    def get_help(positional_args, keyword_args):
        name = text_utils.quote_if_needed(Detector.name)
        arg_descriptors = vcl_utils.parse_command_args_yaml(_ARGS)
        args_help = vcl_utils.create_command_args_help(arg_descriptors)
        return name + ' ' + _HELP + '\n\n' + args_help

    
    def __init__(self, positional_args, keyword_args):
        
        # TODO: Make this more generally available.
        if len(positional_args) != 0:
            s = 's' if len(positional_args) > 1 else ''
            args = ' '.join(positional_args)
            message = 'Extra positional argument{:s}: {:s}'.format(s, args)
            raise CommandSyntaxError(message)
        
        self._detector_names = _get_detector_name(keyword_args)
        self._input_mode = _get_input_mode(keyword_args)
        self._input_paths = \
            vcl_utils.get_required_keyword_arg_tuple('inputs', keyword_args)
        self._detection_handler = _get_detection_handler(keyword_args)
        
                
    def detect(self):
        
        # TODO: Develop Vesper command error handling policy and implement
        # it for this command. As of this writing `os_utils` functions
        # can raise exceptions that are not handled, `AssertionError`
        # exceptions are raised that are not handled, and there may be
        # additional, similar problems.
        
        _check_detection_setup()
        
        if self._input_mode == _INPUT_MODE_FILE:
            
            self._detection_handler.on_detection_start()
            
            try:
                return self._detect_on_dirs_and_files()
            finally:
                self._detection_handler.on_detection_end()
        
        
    def _detect_on_dirs_and_files(self):
        
        delegate = self._detection_handler
        
        (recordings, self._success) = \
            delegate.get_recordings(self._input_paths)
        
        for recording in recordings:
            
            delegate.on_recording_start(recording)
            
            for subrecording in recording.subrecordings:
                self._detect_on_subrecording(subrecording)
                    
            delegate.on_recording_end(recording)
            
        return self._success and delegate._success
                    
                 
    def _detect_on_subrecording(self, subrecording):
        
        file_path = subrecording.file_path
        
        s = 's' if len(self._detector_names) > 1 else ''
        logging.info(
            'Running detector{:s} on file "{:s}"...'.format(s, file_path))
        
        self._detection_handler.on_subrecording_start(subrecording)
        
        file_duration = subrecording.length / float(subrecording.sample_rate)
        
        start_time = time.time()
        
        try:
            self._copy_input_file_channel(
                file_path, subrecording.channel_num,
                subrecording.microphone_name)
        except OSError as e:
            # TODO: Handle this as a fatal error.
            logging.error(str(e))
            self._success = False
            return
        
        processing_time = time.time() - start_time
        _log_performance('Copied', file_duration, processing_time)

        start_time = time.time()
        
        # TODO: set self._success appropriately when there is an error
        # in a detector.
        detectors = self._start_detectors()
        self._wait_for_detectors(detectors)
        
        self._detection_handler.on_subrecording_end(subrecording)
        
        # TODO: Track success on individual recordings. Try to show
        # performance in all cases where it makes sense, even if there
        # were errors.
        if self._success:
            processing_time = time.time() - start_time
            _log_performance(
                'Detection ran on', file_duration, processing_time)
            
            
    def _copy_input_file_channel(
            self, file_path, channel_num, microphone_name):
        
        file_name = os.path.basename(file_path)
        
        logging.info((
            'Copying input file "{}" channel {} (for microphone {}) '
            'to "{}"...').format(
                file_name, channel_num, microphone_name, _INPUT_FILE_PATH))
        
        audio_file_utils.copy_wave_file_channel(
            file_path, channel_num, _INPUT_FILE_PATH)
        
        
    def _start_detectors(self):
        
        detectors = []
        
        for name in self._detector_names:
            
            detector = _Detector(name, self._input_mode, self._on_detection)
            
            logging.info('Starting {:s} detector...'.format(name))
            
            try:
                detector.start()
                
            except OSError as e:
                logging.error((
                    'Could not start "{:s}" detector. Error message '
                    'was: {:s}').format(name, str(e)))
                self._success = False
                
            else:
                detectors.append(detector)
                
        return detectors
    
    
    def _on_detection(self, clip):
        try:
            self._detection_handler.on_detection(clip)
        except DetectionHandlerError as e:
            logging.error((
                'Error processing clip file "{:s}". '
                'Error message was: {:s}').format(clip.file_path, str(e)))
        

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
    
    names = vcl_utils.get_required_keyword_arg_tuple('detectors', keyword_args)
    
    for name in names:
        if name not in _DETECTOR_NAMES:
            message = 'Unrecognized detector "{:s}".'.format(name)
            raise CommandExecutionError(message)
        
    return names


def _get_input_mode(keyword_args):
    
    # TODO: Make --input-mode argument optional, and infer its value
    # in some or all cases?
    
    mode = vcl_utils.get_required_keyword_arg('input-mode', keyword_args)
    
    if mode not in _INPUT_MODES:
        message = 'Unrecognized input mode "{:s}".'.format(mode)
        raise CommandExecutionError(message)
        
    # For now we support only file input.
    if mode != _INPUT_MODE_FILE:
        message = (
            'Sorry, but only the "{:s}" input mode is available at this '
            'time.').format(_INPUT_MODE_FILE)
        raise CommandExecutionError(message)
    
    return mode
    
    
_DETECTION_HANDLER_CLASSES = {
    'MPG Ranch Renamer': DetectionRenamer,
    'Archiver': DetectionArchiver
}


def _get_detection_handler(keyword_args):
    
    handler_name = vcl_utils.get_optional_keyword_arg(
        'detection-handler', keyword_args, 'Archiver')
    
    try:
        klass = _DETECTION_HANDLER_CLASSES[handler_name]
    except KeyError:
        raise CommandSyntaxError(
            'Unrecognized detection handler "{:s}".'.format(handler_name))
        
    return klass(keyword_args)


def _is_audio_file(path):
    return path.endswith('.wav')


def _get_input_file_info(path):
    
    (num_channels, sample_size, frame_rate, num_frames, compression_type) = \
        audio_file_utils.get_wave_file_info(path)
    
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
            'type of "NONE" is currently supported.').format(compression_type))

    return (frame_rate, num_frames)

    
def _log_performance(prefix, file_duration, processing_time):
    
    format_ = text_utils.format_number
    
    dur = format_(file_duration)
    time = format_(processing_time)
    
    message = '{:s} {:s}-second file in {:s} seconds'.format(prefix, dur, time)
    
    if processing_time != 0:
        speedup = format_(file_duration / processing_time)
        message += ', {:s} times faster than real time.'.format(speedup)
    else:
        message += '.'
        
    logging.info(message)


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
        
        # TODO: When detection does not complete normally, vcl detect
        # command needs to return `False`. this currently does not happen.
        
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
                    'Terminating {:s} detector since detector log indicates '
                    'that sound file processing is complete...').format(
                        self.name))
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
        
        logging.info(
            'Creating empty detector log file "{:s}"...'.format(log_path))
        os_utils.create_file(log_path)


    def _is_input_file_exhausted(self):
        
        try:
            contents = os_utils.read_file(self._log_path)
        except OSError:
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
            
        except ValueError as e:
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
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode File
    --inputs ...
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode Live
vesper detect "Old Bird" --detectors Tseep Thrush --input-mode Playback
    --start-time "2014-08-26 07:25:00 MDT"
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
#             message = 'Missing required keyword argument "{:s}".'.format(
#                 name)
#             raise CommandFormatError(message)
#         else:
#             return default
#
#
#     if values is not None and value not in values:
#         message = 'Illegal value "{:s}" for keyword argument'
#         raise CommandFormatError(message)
'''
