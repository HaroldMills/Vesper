"""
The recorder process.

The recorder process is started by the main process and in turn starts all
other recorder processes, referred to as the *recorder subprocesses*. The
recorder process is also responsible for the orderly shutdown of the
recorder subprocesses and itself, either in response to a keyboard
interrupt or the stop thread setting the recorder process's stop event.
"""


# Disable keyboard interrupts for this process. See the
# `vesper.recordex.keyboard_interrupt_disabler` module docstring for
# a discussion of Vesper Recorder keyboard interrupt handling.
import vesper.recordex.keyboard_interrupt_disabler

from datetime import datetime as DateTime, timedelta as TimeDelta
from pathlib import Path
from threading import Event, Thread
from zoneinfo import ZoneInfo
import logging

from vesper.recordex import recorder_utils
from vesper.recordex.audio_input_process import AudioInputProcess
from vesper.recordex.audio_processing_process import AudioProcessingProcess
from vesper.recordex.http_server import HttpServer
from vesper.recordex.process import Process


# TODO: Consider supporting fixed-duration recording, for which a recording
# will end after a specified number of sample frames, rather than when
# the recorder receives a `stop_recording` command. But consider how to deal
# with dropped samples. How much duration was dropped? If we know, perhaps
# we can insert zero samples? If we don't know, when should we stop
# recording? Perhaps we should stop if it would otherwise continue past
# a certain end time, even if we haven't reached the indicated sample
# count.

# TODO: When the recorder shuts down, do we ensure that all audio that
# has arrived has been processed? If not, should we?

# TODO: Consider using a multithreading queue instead of a multiprocessing
# queue for the recorder process's command queue. All commands sent to
# the recorder process currently come from its schedule thread. The UI
# thread will send commands, too, but the UI thread will also be a
# recorder process thread.


_DEFAULT_LOGGING_LEVEL = 'INFO'


_logger = logging.getLogger(__name__)


class VesperRecorderError(Exception):
    pass


class RecorderProcess(Process):


    def __init__(self, settings, logging_level, logging_queue):

        super().__init__(
            'RecorderProcess', settings, logging_level, logging_queue)
        
        self._home_dir_path = Path.cwd()

        s = self._settings
        self._station = s.station
        self._schedule = s.schedule
        self._run_duration = s.run_duration

        self._start_time = DateTime.now(tz=ZoneInfo('UTC'))
        self._recording = False

        
    @property
    def settings(self):
        return self._settings
    

    @property
    def logging_level(self):
        return self._logging_level
    

    @property
    def logging_queue(self):
        return self._logging_queue


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
    

    def _start(self):
        self._recording_processes = []
        self._sidecar_processes = self._start_sidecar_processes()
        self._threads = self._start_threads()
        self._start_http_server()


    def _start_sidecar_processes(self):
        return []
    

    def _start_threads(self):
        threads = (
            self._start_schedule_thread(),
            self._start_quit_thread()
        )
        return tuple(t for t in threads if t is not None)
    

    def _start_schedule_thread(self):
        return self._start_thread(_ScheduleThread, self._command_queue)


    def _start_thread(self, cls, *args):
        thread = cls(*args)
        _logger.info(f'Starting thread "{thread.name}"...')
        thread.start()
        return thread
    

    def _start_quit_thread(self):
        run_duration = self._settings.run_duration
        if run_duration is None:
            return None
        else:
            return self._start_thread(
                _QuitThread, run_duration, self._stop_event)


    def _start_http_server(self):
        port_num = self._settings.server_port_num
        server = HttpServer(port_num, self)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()


    def _do_start_recording(self, command):

        if not self._recording:

            _logger.info('Starting recording...')

            processing_process = AudioProcessingProcess(
                self.settings, self.logging_level, self.logging_queue)
            
            input_process = AudioInputProcess(
                self.settings, self.logging_level, self.logging_queue,
                processing_process.command_queue)
            
            self._recording_processes = [input_process, processing_process]

            # Start recording processes in reverse order so actual audio
            # input starts last.
            for process in reversed(self._recording_processes):
                _logger.info(f'Starting recording process "{process.name}"...')
                process.start()

            self._recording = True


    def _do_stop_recording(self, command):

        if self._recording:

            _logger.info('Stopping recording...')

            self._stop_and_join(
                self._recording_processes, 'recording process',
                'recording processes')

            self._recording_processes = []
            self._recording = False


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

        _logger.info('Recorder process stopping...')

        # Stop recording processes.
        self._stop_and_join(
            self._recording_processes, 'recording process',
            'recording processes')
    
        # Stop sidecar processes.
        self._stop_and_join(
            self._sidecar_processes, 'sidecar process',
            'sidecar processes')
    
        # Stop recorder process threads.
        self._stop_and_join(self._threads, 'thread', 'threads')

        # Close command queue and wait for its feeder thread to exit.
        # We must do this since the schedule thread writes commands
        # to the queue.
        recorder_utils.close_mp_queue(self._command_queue)


class _ScheduleThread(Thread):


    def __init__(self, recorder_process_command_queue):
        super().__init__(name='ScheduleThread')
        self._recorder_process_command_queue = recorder_process_command_queue
        self._schedule = (2, 5, 2, 5)
        self._stop_event = Event()


    @property
    def stop_event(self):
        return self._stop_event
    

    def run(self):
        
        command_queue = self._recorder_process_command_queue
        
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


class _QuitThread(Thread):


    def __init__(self, run_duration, recorder_process_stop_event):
        super().__init__(name='QuitThread')
        self._run_duration = run_duration
        self._recorder_process_stop_event = recorder_process_stop_event
        self._stop_event = Event()


    @property
    def stop_event(self):
        return self._stop_event
    

    def run(self):

        self._stop_event.wait(timeout=self._run_duration)

        if not self._stop_event.is_set():
            # wait timed out

            _logger.info(
                f'Recorder quit thread telling recorder process to stop '
                f'after run duration of {self._run_duration} seconds...')
            
            self._recorder_process_stop_event.set()

        _logger.info('Recorder quit thread exiting...')
