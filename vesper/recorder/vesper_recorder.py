"""Module containing the `VesperRecorder` class."""


from collections.abc import Mapping
from logging import FileHandler, Formatter, StreamHandler
from pathlib import Path
from threading import Thread
from zoneinfo import ZoneInfo
import logging
import time

from vesper.recorder.audio_file_writer import AudioFileWriter
from vesper.recorder.audio_recorder import AudioRecorder, AudioRecorderListener
from vesper.recorder.http_server import HttpServer
from vesper.recorder.level_meter import LevelMeter
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule
import vesper.util.yaml_utils as yaml_utils


# TODO: Make main function `main` instead of `_main`.
# TODO: Make audio file writers processors.
# TODO: Support multiple audio file writers.
# TODO: Support per-recording recording subdirectories.
# TODO: Make level meters processors.
# TODO: Optionally upload recorded files to S3.
# TODO: Optionally upload status updates regularly to S3.
# TODO: Consider updating settings between recordings.
# TODO: Consider supporting S3 setting files.
# TODO: Write daily log files.
# TODO: Optionally upload log files to S3.
# TODO: Compute summary spectrograms and optionally upload them to S3.

# TODO: Review and improve threading/process structure of recorder.
# TODO: Move scheduling from `AudioRecorder` to `VesperRecorder`.
# TODO: Consider using a `VesperRecorderError` exception.
# TODO: Add support for 24-bit input samples.
# TODO: Add support for 32-bit floating point input samples.
# TODO: Consider using `soundfile` package for writing audio files.
# TODO: Consider adding support for additional file formats, e.g. FLAC.

# TODO: If we detect in real time, how will archiving detections
# work? We need a recording to refer to when we archive a clip,
# but the recording will be in progress. Perhaps we create a
# recording in a Vesper archive as soon as the recording
# commences, including its planned length. The length could be
# updated later if needed.
    

_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_SETTINGS_FILE_NAME = 'Vesper Recorder Settings.yaml'

_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_STATION_LATITUDE = None
_DEFAULT_STATION_LONGITUDE = None
_DEFAULT_STATION_TIME_ZONE = 'UTC'
_DEFAULT_INPUT_CHANNEL_COUNT = 1
_DEFAULT_INPUT_SAMPLE_RATE = 22050          # hertz
_DEFAULT_INPUT_SAMPLE_TYPE = 'int16'
_DEFAULT_INPUT_BUFFER_SIZE = .05            # seconds
_DEFAULT_INPUT_TOTAL_BUFFER_SIZE = 60       # seconds
_DEFAULT_SCHEDULE = {}
_DEFAULT_LEVEL_METER_ENABLED = True
_DEFAULT_LEVEL_METER_UPDATE_PERIOD = 1      # seconds
_DEFAULT_LOCAL_RECORDING_ENABLED = True
_DEFAULT_LOCAL_RECORDING_DIR_PATH = 'Recordings'
_DEFAULT_LOCAL_RECORDING_MAX_AUDIO_FILE_DURATION = 3600     # seconds
_DEFAULT_SERVER_PORT_NUM = 8001


_logger = logging.getLogger(__name__)


class VesperRecorderError(Exception):
    pass


class VesperRecorder:
    
    """Records audio to .wav files according to a schedule."""
    
    
    VERSION_NUMBER = '0.3.0a0'


    @staticmethod
    def get_input_devices():
        return AudioRecorder.get_input_devices()
    
    
    @staticmethod
    def create_and_run_recorder(home_dir_path):
        return _create_and_run_recorder(home_dir_path)
    
    
    def __init__(self, settings):
        self._settings = settings

        
    def start(self):
        
        s = self._settings

        self._recorder = _create_audio_recorder(s)

        # Create level meter if needed.
        if s.level_meter.enabled:
            level_meter = LevelMeter(s.level_meter.update_period)
            self._recorder.add_listener(level_meter)
        else:
            level_meter = None

        # Create audio file writer if needed.
        if s.local_recording.enabled:
            local_audio_file_writer = AudioFileWriter(
                s.station.name, s.local_recording.dir_path,
                s.local_recording.max_audio_file_duration)
            self._recorder.add_listener(local_audio_file_writer)
        else:
            local_audio_file_writer = None
         
        # Create HTTP server.
        server = HttpServer(
            s.server_port_num, VesperRecorder.VERSION_NUMBER, s.station,
            self._recorder, level_meter, local_audio_file_writer)
        
        # Start HTTP server.
        Thread(target=server.serve_forever, daemon=True).start()

        # Start recorder.
        self._recorder.start()
         

    def wait(self, timeout=None):
        self._recorder.wait(timeout)
        
        
    def stop(self):
        self._recorder.stop()
        
        
def _create_and_run_recorder(home_dir_path):
    
    _configure_logging(home_dir_path)
    
    _logger.info(f'Welcome to the Vesper Recorder!')
    
    _logger.info(
        f'Recorder version number is {VesperRecorder.VERSION_NUMBER}.')
    
    # Get recorder settings.
    settings_file_path = home_dir_path / _SETTINGS_FILE_NAME
    _logger.info(
        f'Reading recorder settings from file "{settings_file_path}"...')
    try:
        settings = _read_settings_file(settings_file_path, home_dir_path)
    except VesperRecorderError as e:
        _logger.error(f'{e}')
        return
    
    _logger.info(
        f'Starting recorder with home page '
        f'http://localhost:{settings.server_port_num}...')
    
    # Create recorder.
    try:
        recorder = VesperRecorder(settings)
    except Exception as e:
        _logger.error(f'Could not create recorder. Error message was: {e}')
        return
           
    # Start recorder. 
    try:
        recorder.start()
    except Exception as e:
        _logger.error(f'Could not start recorder. Error message was: {e}')
        raise
        return
    
    # Wait for keyboard interrupt.
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    
    _logger.info('Stopping recorder and exiting due to keyboard interrupt...')
    recorder.stop()
    recorder.wait()
         

def _configure_logging(home_dir_path):
    
    # Create handler that writes log messages to stderr.
    stderr_handler = StreamHandler()
    formatter = Formatter('%(asctime)s %(levelname)s %(message)s')
    stderr_handler.setFormatter(formatter)
    
    # Create handler that appends messages to log file.
    log_file_path = home_dir_path / _LOG_FILE_NAME
    file_handler = FileHandler(log_file_path)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    # Add handlers to root logger.
    logger = logging.getLogger()
    logger.addHandler(stderr_handler)
    logger.addHandler(file_handler)
    
    # Set root logger level.
    logger.setLevel(logging.INFO)
        
        
def _read_settings_file(settings_file_path, home_dir_path):

    # Check that settings file exists.
    if not settings_file_path.exists():
        raise VesperRecorderError(
            f'Recorder settings file "{settings_file_path}" does not exist.')
        
    # Parse settings file.
    home_dir_path = settings_file_path.parent
    try:
        return _parse_settings_file(settings_file_path, home_dir_path)
    except Exception as e:
        raise VesperRecorderError(
            f'Could not parse recorder settings file '
            f'"{settings_file_path}". Error message was: {e}')
    

def _parse_settings_file(settings_file_path, home_dir_path):
    
    settings = _Settings(settings_file_path)

    station = _parse_station_settings(settings)
    schedule = _parse_schedule_settings(settings, station)
    input = _parse_input_settings(settings)
    level_meter = _parse_level_meter_settings(settings)
    local_recording = _parse_local_recording_settings(settings, home_dir_path)
        
    server_port_num = int(settings.get(
        'server_port_num', _DEFAULT_SERVER_PORT_NUM))
    
    return Bunch(
        station=station,
        schedule=schedule,
        input=input,
        level_meter=level_meter,
        local_recording=local_recording,
        server_port_num=server_port_num)
    
    
def _parse_station_settings(settings):

    name = settings.get('station.name', _DEFAULT_STATION_NAME)
    lat = settings.get('station.latitude', _DEFAULT_STATION_LATITUDE)
    lon = settings.get('station.longitude', _DEFAULT_STATION_LONGITUDE)
    time_zone = ZoneInfo(
        settings.get('station.time_zone', _DEFAULT_STATION_TIME_ZONE))
    
    return Bunch(
        name=name,
        lat=lat,
        lon=lon,
        time_zone=time_zone)
        

def _parse_schedule_settings(settings, station):

    schedule_dict = settings.get('schedule', _DEFAULT_SCHEDULE)

    return Schedule.compile_dict(
        schedule_dict, latitude=station.lat, longitude=station.lon,
        time_zone=station.time_zone)
    

def _parse_input_settings(settings):

    device_name = settings.get('input.device_name')

    channel_count = int(settings.get(
        'input.channel_count', _DEFAULT_INPUT_CHANNEL_COUNT))
    
    sample_rate = int(settings.get(
        'input.sample_rate', _DEFAULT_INPUT_SAMPLE_RATE))

    buffer_size = float(settings.get(
        'input.buffer_size', _DEFAULT_INPUT_BUFFER_SIZE))
    
    total_buffer_size = float(settings.get(
        'input.total_buffer_size', _DEFAULT_INPUT_TOTAL_BUFFER_SIZE))
    
    settings = Bunch(
        device_name=device_name,
        channel_count=channel_count,
        sample_rate=sample_rate,
        sample_type='int16',
        buffer_size=buffer_size,
        total_buffer_size=total_buffer_size)

    AudioRecorder.check_input_settings(settings)

    return settings


def _parse_level_meter_settings(settings):

    enabled = settings.get('level_meter.enabled', _DEFAULT_LEVEL_METER_ENABLED)

    update_period = float(settings.get(
        'level_meter.update_period', _DEFAULT_LEVEL_METER_UPDATE_PERIOD))
    
    return Bunch(
        enabled=enabled,
        update_period=update_period)
    

def _parse_local_recording_settings(settings, home_dir_path):

    enabled = settings.get(
        'local_recording.enabled', _DEFAULT_LOCAL_RECORDING_ENABLED)
    
    dir_path = Path(settings.get(
        'local_recording.recording_dir_path',
        _DEFAULT_LOCAL_RECORDING_DIR_PATH))
    
    if not dir_path.is_absolute():
        dir_path = home_dir_path / dir_path
        
    max_audio_file_duration = settings.get(
        'local_recording.max_audio_file_duration',
        _DEFAULT_LOCAL_RECORDING_MAX_AUDIO_FILE_DURATION)
    
    return Bunch(
        enabled=enabled,
        dir_path=dir_path,
        max_audio_file_duration=max_audio_file_duration)
    

def _create_audio_recorder(settings):

    # Create audio recorder.
    i = settings.input
    recorder = AudioRecorder(
        i.device_name, i.channel_count, i.sample_rate,
        _DEFAULT_INPUT_SAMPLE_TYPE, i.buffer_size, i.total_buffer_size,
        settings.schedule)
    
    # Create logger.
    recorder.add_listener(_Logger())

    return recorder
    

class _Settings:


    def __init__(self, file_path):
        with open(file_path) as f:
            self._settings = yaml_utils.load(f)


    def get(self, path, default=None):
        
        s = self._settings

        for name in path.split('.'):

            if isinstance(s, Mapping) and name in s:
                s = s[name]
            else:
                return default
            
        # If we get here, the setting is present with value `s`.
        return s


class _Logger(AudioRecorderListener):
    
    
    def __init__(self):
        super().__init__()
        self._portaudio_overflow_buffer_count = 0
        self._recorder_overflow_frame_count = 0
        
        
    def recording_started(self, recorder, time):
        self._sample_rate = recorder.sample_rate
        _logger.info('Started recording.')
        
        
    def input_arrived(
            self, recorder, time, samples, frame_count, portaudio_overflow):
        
        self._log_portaudio_overflow_if_needed(portaudio_overflow)
        self._log_recorder_overflow_if_needed(False)
            
            
    def _log_portaudio_overflow_if_needed(self, overflow):
        
        if overflow:
            
            if self._portaudio_overflow_buffer_count == 0:
                # overflow has just started
                
                _logger.error(
                    'PortAudio input overflow: PortAudio has reported that '
                    'an unspecified number of input samples were dropped '
                    'before or during the current buffer. A second message '
                    'will be logged later indicating the number of '
                    'consecutive buffers for which this error occurred.')
                
            self._portaudio_overflow_buffer_count += 1
            
        else:
            
            if self._portaudio_overflow_buffer_count > 0:
                # overflow has just ended
                
                if self._portaudio_overflow_buffer_count == 1:
                    
                    _logger.error(
                        'PortAudio input overflow: Overflow was reported for '
                        'one buffer.')
                    
                else:
                    
                    _logger.error(
                        f'PortAudio input overflow: Overflow was reported '
                        f'for {self._portaudio_overflow_buffer_count} '
                        f'consecutive buffers.')
            
                self._portaudio_overflow_buffer_count = 0
            

    def _log_recorder_overflow_if_needed(self, overflow, frame_count=0):
        
        if overflow:
            
            if self._recorder_overflow_frame_count == 0:
                # overflow has just started
                
                _logger.error(
                    'Recorder input overflow: The recorder has run out of '
                    'buffers for arriving input samples. It will substitute '
                    'zero samples until buffers become available, and then '
                    'log another message to report the duration of the lost '
                    'samples.')
                
            self._recorder_overflow_frame_count += frame_count
            
        else:
            
            if self._recorder_overflow_frame_count > 0:
                # overflow has just ended
                
                duration = \
                    self._recorder_overflow_frame_count / self._sample_rate
                _logger.error(
                    f'Recorder input overflow: {duration:.3f} seconds of '
                    f'zero samples were substituted for lost input samples.')
                    
                self._recorder_overflow_frame_count = 0
                    
        
    def input_overflowed(
            self, recorder, time, frame_count, portaudio_overflow):
        self._log_portaudio_overflow_if_needed(portaudio_overflow)
        self._log_recorder_overflow_if_needed(True, frame_count)
        
        
    def recording_stopped(self, recorder, time):
        self._log_portaudio_overflow_if_needed(False)
        self._log_recorder_overflow_if_needed(False)
        _logger.info('Stopped recording.')
