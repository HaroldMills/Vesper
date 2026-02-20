"""Main recorder process."""


from logging import Formatter, FileHandler, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from threading import Event, Thread
from zoneinfo import ZoneInfo
import logging
import multiprocessing as mp

from vesper.recorder.settings import Settings
from vesper.recordex import recorder_utils
from vesper.recordex.audio_input_process import AudioInputProcess
from vesper.recordex.audio_processing_process import AudioProcessingProcess
from vesper.recordex.process import Process
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule


# TODO: Consider supporting fixed-duration recording, for which a recording
# will end after a specified number of sample frames, rather than when
# the recorder receives a `stop_recording` command. But consider how to deal
# with dropped samples. How much duration was dropped? If we know, perhaps
# we can insert zero samples? If we don't know, when should we stop
# recording? Perhaps we should stop if it would otherwise continue past
# a certain end time, even if we haven't reached the indicated sample
# count.

# TODO: Consider requiring station settings.

# TODO: Would it make sense to create the logging queue in the main
# process, and then pass it to the recording process and other processes'
# initializers? Would that make starting and stopping logging in all of
# the non-main processes identical?

# TODO: When the recorder shuts down, do we ensure that all audio that
# has arrived has been processed? If not, should we?

# TODO: Consider using a multithreading queue instead of a multiprocessing
# queue for the recorder process's command queue. All commands sent to
# the main process currently come from its schedule thread. I intend for
# the UI thread to send commands, too, but the UI thread will be a thread
# in the main process.


_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_DEFAULT_LOGGING_LEVEL = 'INFO'
_LOGGING_LEVELS = ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')

_SETTINGS_FILE_NAME = 'Vesper Recorder Settings.yaml'
_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_STATION_LATITUDE = None
_DEFAULT_STATION_LONGITUDE = None
_DEFAULT_STATION_TIME_ZONE = 'UTC'
_DEFAULT_SCHEDULE = {}
_DEFAULT_SERVER_PORT_NUM = 8001
_DEFAULT_STOP_TIMEOUT = 5

_PROCESSOR_CLASSES = ()
_SIDECAR_CLASSES = ()


_logger = logging.getLogger(__name__)


class VesperRecorderError(Exception):
    pass


class RecorderProcess(Process):


    def __init__(self):
        super().__init__('RecorderProcess')
        self._home_dir_path = Path.cwd()


    def _start_logging(self):

        """Start logging for the main recorder process."""

        # Create logging queue for all recorder processes to write messages
        # to. The messages are handled by the queue listener created below.
        self._logging_queue = mp.Queue()

        # Create handler that writes log messages to stderr.
        stderr_handler = StreamHandler()
        formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        stderr_handler.setFormatter(formatter)
        
        # Create handler that appends messages to log file.
        log_file_path = self._home_dir_path / _LOG_FILE_NAME
        file_handler = FileHandler(log_file_path)
        formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        # Create logging queue listener that reads messages from the queue
        # and logs them.
        self._logging_queue_listener = QueueListener(
            self._logging_queue, stderr_handler, file_handler)
        self._logging_queue_listener.start()

        # Get the root logger for the main recorder process.
        logger = logging.getLogger()

        # Set logging level to default for now. The level will be updated
        # after the recorder settings file is parsed in case it is specified
        # there.
        logger.setLevel(_DEFAULT_LOGGING_LEVEL)

        # Add handler to root logger that writes all log messages to the
        # recorder's logging queue.
        self._logging_queue_handler = QueueHandler(self._logging_queue)
        logger.addHandler(self._logging_queue_handler)


    def _start(self):

        _logger.info(f'Welcome to the Vesper Recorder!')

        self._settings = self._parse_settings_file()

        _logger.info(
            f'Recorder home page URL is '
            f'"http://localhost:{self._settings.server_port_num}".')
        
        self._logging_level = self._settings.logging_level

        # Update logging level if `logging_level` setting  differs from
        # default.
        if self._logging_level != _DEFAULT_LOGGING_LEVEL:
            _logger.info(
                f'Setting recorder logging level to settings file '
                f'value "{self._logging_level}"...')
            logging.getLogger().setLevel(self._logging_level)
            
        self._recording_processes = []
        self._sidecar_processes = self._start_sidecar_processes()
        self._threads = self._start_threads()


    def _parse_settings_file(self):

        settings_file_path = self._home_dir_path / _SETTINGS_FILE_NAME

        _logger.info(
            f'Reading recorder settings from file "{settings_file_path}"...')
        
        try:
            return _parse_settings_file(settings_file_path)
        except Exception as e:
            _logger.error(str(e))
            raise VesperRecorderError(
                'Could not parse recorder settings file. '
                'See previous log message for details.')


    def _start_sidecar_processes(self):
        return []
    

    def _start_threads(self):
        threads = (
            self._start_schedule_thread(),
            self._start_stop_thread()
        )
        return tuple(t for t in threads if t is not None)
    

    def _start_schedule_thread(self):
        return self._start_thread(_ScheduleThread, self._command_queue)


    def _start_thread(self, cls, *args):
        thread = cls(*args)
        _logger.info(f'Starting thread "{thread.name}"...')
        thread.start()
        return thread
    

    def _start_stop_thread(self):
        run_duration = self._settings.run_duration
        if run_duration is None:
            return None
        else:
            return self._start_thread(
                _StopThread, run_duration, self._stop_event)


    def _do_start_recording(self, command):

        _logger.info('Starting recording...')

        processing_process = AudioProcessingProcess(
            self._settings, self._logging_level, self._logging_queue)
        
        input_process = AudioInputProcess(
            self._settings, self._logging_level, self._logging_queue,
            processing_process.command_queue)
        
        self._recording_processes = [input_process, processing_process]

        # Start recording processes in reverse order so actual audio
        # input starts last.
        for process in reversed(self._recording_processes):
            _logger.info(f'Starting recording process "{process.name}"...')
            process.start()


    def _do_stop_recording(self, command):

        _logger.info('Stopping recording...')

        self._stop_and_join(
            self._recording_processes, 'recording process',
            'recording processes')

        self._recording_processes = []


    def _stop_and_join(self, objects, singular_name, plural_name):

        if len(objects) == 0:
            _logger.info(f'There are no {plural_name} to stop.')
            return True

        else:

            for o in objects:
                _logger.info(f'Telling {singular_name} "{o.name}" to stop...')
                o.stop_event.set()

            stop_timeout = self._settings.stop_timeout

            for o in objects:

                name = f'{singular_name.capitalize()} "{o.name}"'

                recorder_utils.join_with_timeout(
                    o, stop_timeout, _logger, name)
        
                    
    def _stop(self):

        _logger.info('Main process stopping...')

        # Stop recording processes.
        self._stop_and_join(
            self._recording_processes, 'recording process',
            'recording processes')
    
        # Stop sidecar processes.
        self._stop_and_join(
            self._sidecar_processes, 'sidecar process',
            'sidecar processes')
    
        # Stop main process threads.
        self._stop_and_join(self._threads, 'thread', 'threads')

        # Close command queue and wait for its feeder thread to exit.
        # We must do this since the schedule thread writes commands
        # to the queue.
        recorder_utils.close_mp_queue(self._command_queue)

        _logger.info('The Vesper Recorder will now exit.')


    def _stop_logging(self):

        """
        Stop logging for the main recorder process.

        This stops logging for the main process both as a producer of
        log messages and as the manager of the multiprocess logging queue.
        """

        # Drain logging queue and stop queue listener monitor thread.
        # We must do this before we close the logging queue. This is
        # the first of two parts of stopping logging for the main
        # process as the manager of the logging queue.
        self._logging_queue_listener.stop()

        # Close logging queue handler and logging queue. This
        # stops logging for the main process as a producer of
        # log messages.
        super()._stop_logging()

        # Flush and close stream and file handlers. This is the
        # second of two parts of stopping logging for the main
        # process as the manager of the logging queue.
        logging.shutdown()


def _parse_settings_file(settings_file_path):

    # Check that settings file exists.
    if not settings_file_path.exists():
        raise VesperRecorderError(
            f'Recorder settings file "{settings_file_path}" does not exist.')
        
    # Parse settings file.
    try:
        return _parse_settings_file_aux(settings_file_path)
    except Exception as e:
        raise VesperRecorderError(
            f'Could not parse recorder settings file '
            f'"{settings_file_path}". Error message was: {e}')
    

def _parse_settings_file_aux(settings_file_path):
    
    settings = Settings.create_from_yaml_file(settings_file_path)

    logging_level = _parse_logging_level_setting(settings)
    station = _parse_station_settings(settings)
    schedule = _parse_schedule_settings(settings, station)
    run_duration = _parse_run_duration_settings(settings)
    input = _parse_input_settings(settings)
    processors = _parse_processor_settings(settings)
    sidecars = _parse_sidecar_settings(settings)

    server_port_num = int(settings.get(
        'server_port_num', _DEFAULT_SERVER_PORT_NUM))

    stop_timeout = float(settings.get(
        'stop_timeout', _DEFAULT_STOP_TIMEOUT))

    return Bunch(
        logging_level=logging_level,
        station=station,
        schedule=schedule,
        run_duration=run_duration,
        input=input,
        processors=processors,
        sidecars=sidecars,
        server_port_num=server_port_num,
        stop_timeout=stop_timeout)


def _parse_logging_level_setting(settings):
    value = settings.get('logging_level', _DEFAULT_LOGGING_LEVEL)
    Settings.check_enum_value(value, _LOGGING_LEVELS, 'recorder logging level')
    return value


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
    

def _parse_run_duration_settings(settings):

    value = settings.get('run_duration', None)

    if value is None:
        return value

    def handle_bad_value():
        raise ValueError(
            f'Bad value "{value}" for "run_duration" setting. Value '
            f'must be of the form "<number> <units>" where <number> '
            f'is a nonnegative number and <units> is "days", "hours", '
            f'"minutes", "seconds", or the singular of one of those.')

    if not isinstance(value, str):
        handle_bad_value()

    parts = value.split()

    if len(parts) != 2:
        handle_bad_value()
    
    number, units = parts

    try:
        number = float(number)
    except ValueError:
        handle_bad_value()

    if number < 0:
        handle_bad_value()

    match units:
        case 'days':
            unit_size = 24 * 3600
        case 'day':
            unit_size = 24 * 3600
        case 'hours':
            unit_size = 3600
        case 'hour':
            unit_size = 3600
        case 'minutes':
            unit_size = 60
        case 'minute':
            unit_size = 60
        case 'seconds':
            unit_size = 1
        case 'second':
            unit_size = 1
        case _:
            handle_bad_value()

    return number * unit_size


def _parse_input_settings(settings):
    return Bunch()
    # mapping = settings.get_required('input')
    # settings = Settings(mapping)
    # return AudioInput.parse_settings(settings)


def _parse_processor_settings(settings):

    processor_classes = {cls.type_name: cls for cls in _PROCESSOR_CLASSES}

    settings = settings.get_required('processors')

    return [
        _parse_processor_settings_aux(s, processor_classes)
        for s in settings]


def _parse_processor_settings_aux(mapping, processor_classes):

    settings = Settings(mapping)

    name = settings.get_required('name')
    type = settings.get_required('type')
    input = settings.get_required('input')
    mapping = settings.get('settings', {})

    try:
        cls = processor_classes[type]
    except KeyError:
        raise ValueError(f'Unrecognized processor type "{type}".')
    
    settings = cls.parse_settings(Settings(mapping))

    return Bunch(
        name=name,
        type=type,
        input=input,
        settings=settings)


def _parse_sidecar_settings(settings):

    sidecar_classes = {cls.type_name: cls for cls in _SIDECAR_CLASSES}

    settings = settings.get('sidecars')

    if settings is None:
        return []
    
    else:
        return [
            _parse_sidecar_settings_aux(s, sidecar_classes)
            for s in settings]


def _parse_sidecar_settings_aux(mapping, sidecar_classes):

    settings = Settings(mapping)

    name = settings.get_required('name')
    type = settings.get_required('type')
    mapping = settings.get('settings', {})

    try:
        cls = sidecar_classes[type]
    except KeyError:
        raise ValueError(f'Unrecognized sidecar type "{type}".')
    
    settings = cls.parse_settings(Settings(mapping))

    return Bunch(name=name, type=type, settings=settings)


class _ScheduleThread(Thread):


    def __init__(self, main_process_command_queue):
        super().__init__(name='ScheduleThread')
        self._main_process_command_queue = main_process_command_queue
        self._schedule = (1, 5, 1, 5)
        self._stop_event = Event()


    @property
    def stop_event(self):
        return self._stop_event
    

    def run(self):
        
        command_queue = self._main_process_command_queue
        
        recording = False

        for i, duration in enumerate(self._schedule):

            if i != 0:

                if recording:
                    command_queue.put('stop_recording')
                else:
                    command_queue.put('start_recording')

                recording = not recording

            if self._stop_event.wait(timeout=duration):
                # stop event set

                break

        if recording:
            command_queue.put('stop_recording')

        _logger.info('Recording schedule thread exiting...')


class _StopThread(Thread):


    def __init__(self, run_duration, main_process_stop_event):
        super().__init__(name='StopThread')
        self._run_duration = run_duration
        self._main_process_stop_event = main_process_stop_event
        self._stop_event = Event()


    @property
    def stop_event(self):
        return self._stop_event
    

    def run(self):

        self._stop_event.wait(timeout=self._run_duration)

        if not self._stop_event.is_set():
            # wait timed out

            _logger.info(
                f'Recorder stop thread telling main process to stop '
                f'after run duration of {self._run_duration} seconds...')
            
            self._main_process_stop_event.set()

        _logger.info('Recorder stop thread exiting...')
