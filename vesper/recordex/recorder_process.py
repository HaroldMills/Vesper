"""
Base class for all recorder processes, including both main process and
subprocesses.
"""


import logging
import multiprocessing as mp
import queue

from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


# TODO: Consider supporting two kinds of stop, quick and leisurely.
# A leisurely stop will execute all commands that were queued before the
# stop was requested. A quick stop will finish executing the current
# command (if there is one) and then ignore any others that are in the
# queue. We have implemented only the quick stop below. The leisurely
# stop could be implemented by stopping with a command instead of an
# event. If you want to offer both options, though, use an event and
# a flag indicating which type of stop is desired.


class RecorderProcess(mp.Process):


    def __init__(self, name):
        super().__init__(name=name)
        self._command_queue = mp.Queue()
        self._stop_event = mp.Event()


    def run(self):
        self._set_up_logging()
        self._init()
        self._execute_run_loop()
        self._stop()
        self._tear_down_logging()


    def _set_up_logging(self):
        raise NotImplementedError()
    

    def _init(self):
        pass


    def _execute_run_loop(self):

        while not self._stop_event.is_set():

            try:
                command = self._command_queue.get(timeout=1)
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


    def start_recording(self):
        command = Bunch(name='start_recording')
        self._command_queue.put(command)


    def stop_recording(self):
        command = Bunch(name='stop_recording')
        self._command_queue.put(command)


    def stop(self):
        self._stop_event.set()


    def _do_start_recording(self, command):
        pass


    def _do_stop_recording(self, command):
        pass


    def _stop(self):
        pass


    def _tear_down_logging(self):
        raise NotImplementedError()
