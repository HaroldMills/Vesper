"""Module containing the `VesperRecorder` class."""


from datetime import datetime as DateTime, timedelta as TimeDelta
from logging import FileHandler, Formatter, StreamHandler
from queue import Queue
from threading import Thread
from zoneinfo import ZoneInfo
import logging
import sys
import time

from vesper.recorder.audio_file_writer import AudioFileWriter
from vesper.recorder.audio_input import AudioInput
from vesper.recorder.http_server import HttpServer
from vesper.recorder.level_meter import LevelMeter
from vesper.recorder.processor_graph import ProcessorGraph
from vesper.recorder.resampler import Resampler
from vesper.recorder.settings import Settings
from vesper.util.bunch import Bunch
from vesper.util.schedule import Schedule, ScheduleRunner


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
_SETTINGS_FILE_NAME = 'Vesper Recorder Settings.yaml'

_DEFAULT_STATION_NAME = 'Vesper'
_DEFAULT_STATION_LATITUDE = None
_DEFAULT_STATION_LONGITUDE = None
_DEFAULT_STATION_TIME_ZONE = 'UTC'
_DEFAULT_SCHEDULE = {}
_DEFAULT_SERVER_PORT_NUM = 8001

_PROCESSOR_CLASSES = (Resampler, LevelMeter, AudioFileWriter)


_logger = logging.getLogger(__name__)


class VesperRecorderError(Exception):
    pass


class VesperRecorder:
    
    """Records audio to .wav files according to a schedule."""
    
    
    VERSION_NUMBER = '0.3.0a1'


    @staticmethod
    def create_and_run_recorder(home_dir_path):
        return _create_and_run_recorder(home_dir_path)
    
    
    def __init__(self, settings):
        self._settings = settings

        
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
    def input(self):
        return self._input
    

    @property
    def processor_graph(self):
        return self._processor_graph
    
    
    @property
    def recording(self):
        return self._recording
    

    def run(self):
        
        self._recording = False
        self._stop_pending = False
        self._command_queue = Queue()

        s = self._settings

        self._station = s.station

        self._schedule = s.schedule

        self._start_time = DateTime.now(tz=ZoneInfo('UTC'))
        self._run_duration = s.run_duration

        # Create audio input.
        self._input = self._create_audio_input(s.input)

        # Create processor graph.
        self._processor_graph = ProcessorGraph(
            'Processor Graph', s.processors, self._input, _PROCESSOR_CLASSES)

        self._start_http_server(s.server_port_num)

        self._start_schedule_thread()

        self._start_quit_thread_if_needed()

        while True:
            self._execute_next_command()


    def _create_audio_input(self, settings):
        s = settings
        return AudioInput(
            self, s.device, s.channel_count, s.sample_rate, s.sample_format,
            s.port_audio_block_size, s.buffer_capacity, s.chunk_size)
    

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
        #        step 3.
        #
        #     5. Before main thread calls `_stop_if_pending`, input
        #        thread queues another `process_input` command.
        #
        #     6. Main thread finishes executing command of step 3,
        #        including calling `_stop_if_pending`, which stops
        #        the processor graph.
        #
        #     7. Main thread executes `process_input` command of step 5.
        #        Without the `self._recording` test, it calls
        #        `self._processor_graph.process`, which raises an
        #        exception since the graph was stopped in step 6.

        if self._recording:

            if command.port_audio_overflow:
                self._handle_port_audio_input_overflow()

            chunk = command.chunk

            input_item = Bunch(
                samples=chunk.samples,
                frame_count=chunk.size)

            self._processor_graph.process(input_item)

            # Free sample buffer for reuse.
            self._input.free_chunk(chunk)
            
            self._stop_if_pending()


    def _handle_port_audio_input_overflow(self):

        self._port_audio_input_overflows += 1

        _logger.warning(
            f'Input overflow {self._port_audio_input_overflows} '
            f'reported by PortAudio.')


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

        # It is important to test `self._recording` here, for reasons
        # similar to those of the comments in the `_on_process_input`
        # method.
        if self._recording:
            self._stop_if_pending()


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
        # the `_on_handle_input` or `_on_handle_input_overflow`
        # method *after* processing the next buffer of input samples.
        # If we stop here, for some reason we usually record one less
        # buffer than one would expect from the recording schedule.
        if self._recording:
            self._stop_pending = True


    def _stop_if_pending(self):
        
        if self._stop_pending:
            self._stop()


    def _stop(self):
            
        self._recording = False
        self._stop_pending = False

        self._input.stop()

        self._processor_graph.stop()

        _logger.info('Stopped recording.')


    def quit(self):

        """
        Queues a `quit` command.

        This method can be called from any thread.
        """
        
        command = Bunch(name='quit')
        self._command_queue.put(command)


    def _on_quit(self, command):

        _logger.info('Quitting...')

        if self._recording:
            self._stop()

        sys.exit()

        
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
        settings = _parse_settings_file(settings_file_path, home_dir_path)
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
           
    # Run recorder. 
    try:
        recorder.run()
    except Exception as e:
        _logger.error(f'Recorder raised exception. Error message was: {e}')
        raise
    except KeyboardInterrupt:
        _logger.info(
            'Stopping recorder and exiting due to keyboard interrupt...')
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
        
        
def _parse_settings_file(settings_file_path, home_dir_path):

    # Check that settings file exists.
    if not settings_file_path.exists():
        raise VesperRecorderError(
            f'Recorder settings file "{settings_file_path}" does not exist.')
        
    # Parse settings file.
    try:
        return _parse_settings_file_aux(settings_file_path, home_dir_path)
    except Exception as e:
        raise VesperRecorderError(
            f'Could not parse recorder settings file '
            f'"{settings_file_path}". Error message was: {e}')
    

def _parse_settings_file_aux(settings_file_path, home_dir_path):
    
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


# class _Logger(AudioRecorderListener):
    
    
#     def __init__(self):
#         super().__init__()
#         self._portaudio_overflow_buffer_count = 0
#         self._recorder_overflow_frame_count = 0
        
        
#     def recording_started(self, recorder, time):
#         self._sample_rate = recorder.sample_rate
#         _logger.info('Started recording.')
        
        
#     def input_arrived(
#             self, recorder, time, samples, frame_count, portaudio_overflow):
        
#         self._log_portaudio_overflow_if_needed(portaudio_overflow)
#         self._log_recorder_overflow_if_needed(False)
            
            
#     def _log_portaudio_overflow_if_needed(self, overflow):
        
#         if overflow:
            
#             if self._portaudio_overflow_buffer_count == 0:
#                 # overflow has just started
                
#                 _logger.error(
#                     'PortAudio input overflow: PortAudio has reported that '
#                     'an unspecified number of input samples were dropped '
#                     'before or during the current buffer. A second message '
#                     'will be logged later indicating the number of '
#                     'consecutive buffers for which this error occurred.')
                
#             self._portaudio_overflow_buffer_count += 1
            
#         else:
            
#             if self._portaudio_overflow_buffer_count > 0:
#                 # overflow has just ended
                
#                 if self._portaudio_overflow_buffer_count == 1:
                    
#                     _logger.error(
#                         'PortAudio input overflow: Overflow was reported for '
#                         'one buffer.')
                    
#                 else:
                    
#                     _logger.error(
#                         f'PortAudio input overflow: Overflow was reported '
#                         f'for {self._portaudio_overflow_buffer_count} '
#                         f'consecutive buffers.')
            
#                 self._portaudio_overflow_buffer_count = 0
            

#     def _log_recorder_overflow_if_needed(self, overflow, frame_count=0):
        
#         if overflow:
            
#             if self._recorder_overflow_frame_count == 0:
#                 # overflow has just started
                
#                 _logger.error(
#                     'Recorder input overflow: The recorder has run out of '
#                     'buffers for arriving input samples. It will substitute '
#                     'zero samples until buffers become available, and then '
#                     'log another message to report the duration of the lost '
#                     'samples.')
                
#             self._recorder_overflow_frame_count += frame_count
            
#         else:
            
#             if self._recorder_overflow_frame_count > 0:
#                 # overflow has just ended
                
#                 duration = \
#                     self._recorder_overflow_frame_count / self._sample_rate
#                 _logger.error(
#                     f'Recorder input overflow: {duration:.3f} seconds of '
#                     f'zero samples were substituted for lost input samples.')
                    
#                 self._recorder_overflow_frame_count = 0
                    
        
#     def input_overflowed(
#             self, recorder, time, frame_count, portaudio_overflow):
#         self._log_portaudio_overflow_if_needed(portaudio_overflow)
#         self._log_recorder_overflow_if_needed(True, frame_count)
        
        
#     def recording_stopped(self, recorder, time):
#         self._log_portaudio_overflow_if_needed(False)
#         self._log_recorder_overflow_if_needed(False)
#         _logger.info('Stopped recording.')
