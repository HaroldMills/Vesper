"""Module containing the `VesperRecorder` class."""


from datetime import datetime as DateTime, timedelta as TimeDelta
from logging import Formatter, FileHandler, StreamHandler
from queue import Queue
from threading import Thread
from zoneinfo import ZoneInfo
import logging
import multiprocessing
import sys
import time

from vesper.recorder.audio_file_writer import AudioFileWriter
from vesper.recorder.audio_input import AudioInput
from vesper.recorder.http_server import HttpServer
from vesper.recorder.level_meter import LevelMeter
from vesper.recorder.processor_graph import ProcessorGraph
from vesper.recorder.resampler import Resampler
from vesper.recorder.s3_file_uploader import S3FileUploader
from vesper.recorder.settings import Settings
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule, ScheduleRunner
import vesper.recorder.error_utils as error_utils


# TODO: Consider making processor input and output items 2-D NumPy
#       arrays of float32 samples, with the second element of the
#       shape the frame count. I think this would simplify many
#       processors.
# TODO: Consider whether or not it would be possible to efficiently
#       decouple processor output write sizes from input read sizes.
#       It would make it much easier to implement many processors if
#       they could receive input in chunks (perhaps even overlapping
#       ones) of a size that was convenient for them, instead of
#       for whoever happened to produce them. One option might be to
#       implement an input buffer that a processor could optionally
#       use to write its input to and receive back chunks of a
#       specified size. It would probably make sense for the chunks
#       to be delivered to the processor via a callback that
#       processes them and returns output chunks.
# TODO: Minimize memory churn in processors.
# TODO: Consider implementing recorder `wait` method.
# TODO: Consider modifying schedule notifier to notify only when schedule
#       intervals start, and to include in the notification the interval
#       duration. The recorder could then compute and record the
#       corresponding number of sample frames. Then we could always
#       record the correct number of sample frames do away with the
#       the kludgy `_stop_pending` attribute.
# TODO: Consider allowing partial input chunk at end of recording.
# TODO: Optionally upload status updates regularly to S3.
# TODO: Consider updating settings between recordings.
# TODO: Consider supporting S3 setting files.
# TODO: Write daily log files.
# TODO: Optionally upload log files to S3.
# TODO: Compute summary spectrograms and optionally upload them to S3.
# TODO: Consider making processor inputs and outputs objects.
# TODO: Consider supporting processors with multiple inputs and/or outputs.
# TODO: Consider making audio input a processor.
# TODO: Make processor classes plugins.

# TODO: Include station name in UI title.
# TODO: Include version number in UI.
# TODO: Make main function `main` instead of `_main`.
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
_LOGGING_LEVEL = logging.INFO
_SETTINGS_FILE_NAME = 'Vesper Recorder Settings.yaml'

_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_STATION_LATITUDE = None
_DEFAULT_STATION_LONGITUDE = None
_DEFAULT_STATION_TIME_ZONE = 'UTC'
_DEFAULT_SCHEDULE = {}
_DEFAULT_SERVER_PORT_NUM = 8001

_PROCESSOR_CLASSES = (Resampler, LevelMeter, AudioFileWriter, S3FileUploader)


_logger = logging.getLogger(__name__)


class VesperRecorderError(Exception):
    pass


class VesperRecorder:
    
    """Records audio to .wav files according to a schedule."""
    
    
    VERSION_NUMBER = '0.3.0a3'


    @staticmethod
    def create_and_run_recorder(home_dir_path):
        try:
            return _create_and_run_recorder(home_dir_path)
        except KeyboardInterrupt:
            import sys
            print(
                'Recorder exiting immediately due to keyboard interrupt.',
                file=sys.stderr)
        except Exception:
            error_utils.handle_top_level_exception('Main recorder process')
    
    
    def __init__(self, settings):

        self._settings = settings

        s = self._settings

        self._station = s.station

        self._schedule = s.schedule

        self._start_time = DateTime.now(tz=ZoneInfo('UTC'))
        self._run_duration = s.run_duration

        self._recording = False
        self._input = None
        self._processor_graph = None

        
    @property
    def station(self):
        return self._station
    

    @property
    def schedule(self):
        return self._schedule
    
    
    @property
    def start_time(self):
        return self._start_time
    

    @property
    def run_duration(self):
        return self._run_duration
    

    @property
    def quit_time(self):
        if self.run_duration is None:
            return None
        else:
            run_duration = TimeDelta(seconds=self.run_duration)
            return self.start_time + run_duration
    
    
    @property
    def recording(self):
        return self._recording
    

    @property
    def input(self):
        return self._input
    

    @property
    def processor_graph(self):
        return self._processor_graph
    

    def run(self):
        
        s = self._settings

        self._start_multiprocess_logging_thread()

        # Create audio input.
        self._input = self._create_audio_input(s.input)

        # Create processor graph.
        self._processor_graph = self._create_processor_graph(s.processors)

        self._stop_pending = False
        self._command_queue = Queue()
        
        self._start_http_server(s.server_port_num)

        self._start_schedule_thread()

        self._start_quit_thread_if_needed()

        while True:
            self._execute_next_command()


    def _start_multiprocess_logging_thread(self):
        self._multiprocess_logging_thread = _MultiprocessLoggingThread()
        self._multiprocess_logging_thread.start()


    def _create_audio_input(self, settings):
        s = settings
        return AudioInput(
            self, s.device, s.channel_count, s.sample_rate, s.sample_format,
            s.port_audio_block_size, s.buffer_capacity, s.chunk_size)
    

    def _create_processor_graph(self, settings):

        context = Bunch(
            multiprocess_logging_queue=\
                self._multiprocess_logging_thread.logging_queue,
            processor_classes=_PROCESSOR_CLASSES)

        return ProcessorGraph(
            'Processor Graph', settings, context, self._input)


    def _start_http_server(self, port_num):
        server = HttpServer(port_num, VesperRecorder.VERSION_NUMBER, self)
        Thread(target=server.serve_forever, daemon=True).start()


    def _start_schedule_thread(self):

        self._schedule_runner = ScheduleRunner(self._schedule)

        listener = _ScheduleListener(self)
        self._schedule_runner.add_listener(listener)

        self._schedule_runner.start()


    def _start_quit_thread_if_needed(self):

        run_duration = self._settings.run_duration

        if run_duration is not None:
            thread = _QuitThread(self, run_duration)
            thread.start()


    def _execute_next_command(self):

        # Get next command from queue, waiting if necessary.
        command = self._command_queue.get()

        # Execute command.
        method_name = '_on_' + command.name
        method = getattr(self, method_name)
        method(command)

    
    def start(self):

        """
        Queues a `start` command.

        This method can be called from any thread.
        """
        
        command = Bunch(name='start')
        self._command_queue.put(command)
            
    
    def _on_start(self, command):
        
        """
        Executes a `start` command.

        This method always runs on the main thread.
        """
        
        if not self._recording:

            _logger.info('Starting recording...')

            self._port_audio_input_overflows = 0
            self._recorder_input_overflows = 0

            self._recording = True
            self._stop_pending = False

            self._processor_graph.start()
            self._input.start()


    def process_input(self, chunk, port_audio_overflow):
        
        """
        Queues a `process_input` command.

        This method can be called from any thread.
        """
        
        command = Bunch(
            name='process_input',
            chunk=chunk,
            port_audio_overflow=port_audio_overflow)
        
        self._command_queue.put(command)


    def _on_process_input(self, command):

        """
        Executes a `process_input` command.

        This method always runs on the main thread.
        """
        
        # It is important to test `self._recording` here. Without the
        # test, a race condition involving the input thread and the
        # main thread can cause this method to invoke the processor
        # graph's `process` method after the graph has been stopped,
        # causing it to raise an exception. The race condition can
        # play out as follows:
        #
        #     1. Schedule queues a `stop` command.
        #
        #     2. Main thread executes `stop` command, setting `_stop_pending`.
        #
        #     3. Input thread queues a `process_input` command.
        #
        #     4. Main thread begins executing `process_input` command of
        #        step 3 by executing this method.
        #
        #     5. Before main thread calls `_processor_graph.process`,
        #        input thread queues another `process_input` command.
        #
        #     6. Main thread finishes executing command of step 3,
        #        including calling `_processor_graph.process` with its
        #        `finished` argument `True`. This causes the graph and
        #        all of its processors to stop running.
        #
        #     7. Main thread executes `process_input` command of step 5.
        #        Without the `self._recording` test, it calls
        #        `_processor_graph.process`, which raises an exception
        #        since the graph stopped running in step 6.

        if self._recording:

            if command.port_audio_overflow:
                self._handle_port_audio_input_overflow()

            chunk = command.chunk

            input_item = Bunch(
                samples=chunk.samples,
                frame_count=chunk.size)

            self._processor_graph.process(input_item, self._stop_pending)

            # Free sample buffer for reuse.
            self._input.free_chunk(chunk)
            
            if self._stop_pending:
                self._stop()


    def _handle_port_audio_input_overflow(self):

        self._port_audio_input_overflows += 1

        _logger.warning(
            f'Input overflow {self._port_audio_input_overflows} '
            f'reported by PortAudio.')


    def _stop(self):
            
        self._recording = False
        self._stop_pending = False

        self._input.stop()

        _logger.info('Stopped recording.')


    def handle_input_overflow(self, frame_count, port_audio_overflow):

        """
        Queues a `handle_input_overflow` command.

        This method can be called from any thread.
        """
        
        command = Bunch(
            name='handle_input_overflow',
            frame_count=frame_count,
            port_audio_overflow=port_audio_overflow)
        
        self._command_queue.put(command)


    def _on_handle_input_overflow(self, command):
        
        """
        Executes a `handle_input_overflow` command.

        This method always runs on the main thread.
        """
        
        # TODO: Consider processing a buffer of zeros here,
        # allocated before input starts. This would have some
        # advantages, for example by giving affected audio files the
        # correct lengths and making it more apparent in the files
        # where input was dropped.

        self._recorder_input_overflows += 1
        _logger.warning(
            f'Input overflow {self._recorder_input_overflows} reported '
            f'by recorder audio input.')
        
        if command.port_audio_overflow:
            self._handle_port_audio_input_overflow()

        # Note that we never stop recording in this method, but only
        # in the `_on_process_input` method. This ensures that when we
        # stop each processor hears about it via the `finished` argument
        # of its `process` method.


    # TODO: Implement this.
    def wait(self, timeout=None):
        pass
        
        
    def stop(self):

        """
        Queues a `stop` command.

        This method can be called from any thread.
        """
        
        command = Bunch(name='stop')
        self._command_queue.put(command)


    def _on_stop(self, command):

        """
        Executes a `stop` command.

        This method always runs on the main thread.
        """
        
        # Instead of stopping input here, we set a flag to indicate
        # that a stop is pending, and then stop in the next call to
        # the `_on_handle_input` method *after* processing the next
        # buffer of input samples. This allows that method to notify
        # all of the processors that recording is ending.
        if self._recording:
            self._stop_pending = True


    def quit(self):

        """
        Queues a `quit` command.

        This method can be called from any thread.
        """
        
        command = Bunch(name='stop')
        self._command_queue.put(command)

        command = Bunch(name='quit')
        self._command_queue.put(command)


    def _on_quit(self, command):
        _logger.info('Quitting...')
        sys.exit()

        
def _create_and_run_recorder(home_dir_path):
    
    # Use the `spawn` multiprocessing start method on all platforms.
    # As of Python 3.12, this is the default for Windows and macOS
    # but not for POSIX. On POSIX the default start method is `fork`,
    # which is fast but copies more parent process state to the child
    # process than we need or want. The extra state can cause problems.
    # For example, in an earlier version of the recorder's multiprocess
    # logging system it caused some log messages to be duplicated on
    # POSIX.
    #
    # Note that according to the Python 3.12.4 documentation for the
    # `multiprocessing` module (see https://docs.python.org/3/library/
    # multiprocessing.html#contexts-and-start-methods), the default
    # start method for POSIX will change away from `fork` for Python
    # 3.14. If after that change it is `spawn` (or something else we
    # can work with) for all platforms, we might no longer need to
    # set it explicitly.
    multiprocessing.set_start_method('spawn')

    _configure_logging(_LOGGING_LEVEL, home_dir_path)
    
    _logger.info(f'Welcome to the Vesper Recorder!')
    
    _logger.info(
        f'Recorder version number is {VesperRecorder.VERSION_NUMBER}.')
    
    # Get recorder settings.
    settings_file_path = home_dir_path / _SETTINGS_FILE_NAME
    _logger.info(
        f'Reading recorder settings from file "{settings_file_path}"...')
    try:
        settings = _parse_settings_file(settings_file_path)
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
           
    recorder.run()
        

def _configure_logging(logging_level, home_dir_path):

    # Get the root logger for the main Vesper Recorder process.
    logger = logging.getLogger()

    # Add handler that writes log messages to stderr.
    stderr_handler = StreamHandler()
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)
    
    # Add handler that appends messages to log file.
    log_file_path = home_dir_path / _LOG_FILE_NAME
    file_handler = FileHandler(log_file_path)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Set logging level.
    logger.setLevel(logging_level)


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

    station = _parse_station_settings(settings)
    schedule = _parse_schedule_settings(settings, station)
    run_duration = _parse_run_duration_settings(settings)
    input = _parse_input_settings(settings)
    processors = _parse_processor_settings(settings)
        
    server_port_num = int(settings.get(
        'server_port_num', _DEFAULT_SERVER_PORT_NUM))
    
    return Bunch(
        station=station,
        schedule=schedule,
        run_duration=run_duration,
        input=input,
        processors=processors,
        server_port_num=server_port_num)
    
    
def _parse_station_settings(settings):

    # TODO: Require station settings.
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

    # TODO: Require schedule.
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
    mapping = settings.get_required('input')
    settings = Settings(mapping)
    return AudioInput.parse_settings(settings)


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


class _MultiprocessLoggingThread(Thread):

    """
    Thread within the main Vesper Recorder process that receives log
    records from other recorder processes via a `multiprocessing.Queue`
    and logs them. This is needed since logging via the Python
    Standard Library `logging` module is not multiprocess-safe (it is
    only thread-safe).

    This class is inspired by code that appears in the *Logging to a
    single file from multiple processes* section of the Python Logging
    Cookbook (https://docs.python.org/3/howto/logging-cookbook.html#
    logging-to-a-single-file-from-multiple-processes).
    """


    def __init__(self):
        super().__init__(daemon=True)
        self._logging_queue = multiprocessing.Queue()


    @property
    def logging_queue(self):
        return self._logging_queue
    

    def run(self):

        while True:

            # Get next log record from queue.
            record = self._logging_queue.get()

            if record is None:
                # we're being told to stop

                break

            logger = logging.getLogger(record.name)
            logger.handle(record)


class _ScheduleListener:
    
    
    def __init__(self, recorder):
        self._recorder = recorder
        
        
    def schedule_run_started(self, schedule, time, state):
        if state:
            self._recorder.start()
    
    
    def schedule_state_changed(self, schedule, time, state):
        if state:
            self._recorder.start()
        else:
            self._recorder.stop()
    
    
    def schedule_run_stopped(self, schedule, time, state):
        self._recorder.stop()
    
    
    def schedule_run_completed(self, schedule, time, state):
        self._recorder.stop()


class _QuitThread(Thread):


    def __init__(self, recorder, run_duration):
        super().__init__(daemon=True)
        self.recorder = recorder
        self.run_duration = run_duration


    def run(self):

        start_time = time.time()

        time.sleep(self.run_duration)

        end_time = time.time()
        duration = end_time - start_time

        _logger.info(
            f'Recorder quit thread awoke after sleeping for '
            f'{duration:.1f} seconds. Will now send quit command '
            f'to recorder.')
       
        self.recorder.quit()
