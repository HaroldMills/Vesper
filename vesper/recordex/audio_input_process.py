from threading import Event, Thread
import logging
import queue
import time


from vesper.recordex.recorder_subprocess import RecorderSubprocess
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


class AudioInputProcess(RecorderSubprocess):


    def __init__(self, settings, context, processing_command_queue):
        super().__init__('Audio Input', settings, context)
        self._processing_command_queue = processing_command_queue


    def _init(self):

        _logger.info('Audio input process initializing.')

        # Create private command queue for audio input thread to send
        # commands to the main thread (i.e. this thread) via.
        self._private_command_queue = queue.Queue()

        # Create and start audio input thread.
        self._input_thread = _AudioInputThread(self._private_command_queue)
        self._input_thread.start()


    def _execute_run_loop(self):

        """
        Execute process run loop. This is much like the superclass's
        run loop, except that it uses a private, multithreading command
        queue instead of a multiprocessing command queue. Using a
        threading queue instead of a multiprocessing queue allows the
        audio input callback to run more efficiently.
        """

        while not self._stop_event.is_set():

            try:
                command = self._private_command_queue.get(timeout=1)
            except queue.Empty:
                continue

            method_name = f'_do_{command.name}'

            try:
                method = getattr(self, method_name)
            except AttributeError:
                _logger.warning(f'Unrecognized command "{command.name}".')
                continue

            try:
                method(command)
            except Exception as e:
                _logger.warning(
                    f'Error executing command "{command.name}". '
                    f'Exception message was: {e}')


    def _do_process_audio(self, command):
        _logger.info(
            'Audio input process received "process_audio" command.')
        self._processing_command_queue.put(command)


    def _stop(self):
        _logger.info('Audio input process stopping input thread...')
        self._input_thread.stop()
        self._input_thread.join()
        _logger.info('Audio input process input thread stopped.')


class _AudioInputThread(Thread):


    def __init__(self, command_queue):
        super().__init__()
        self._command_queue = command_queue
        self._stop_event = Event()


    def run(self):
        while not self._stop_event.is_set():
           time.sleep(.1)
           command = Bunch(name='process_audio')
           self._command_queue.put(command)


    def stop(self):
        self._stop_event.set()
