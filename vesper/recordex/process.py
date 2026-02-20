"""
Base class for all recorder processes, including both the main process and
its subprocesses.
"""


import logging
import multiprocessing as mp
import queue
import signal
import sys

from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


# TODO: Document recorder processes, including lifecycle phases (logging
# start, start, run, stop, and logging stop), logging queue, stop event,
# and command queue.

# TODO: Consider adding initializer argument that controls whether or not
# initializer creates a multiprocessing command queue, a multithreading
# command queue, or no command queue.


class _MethodExecutionError(Exception):
    pass


class Process(mp.Process):


    def __init__(self, name):
        super().__init__(name=name)
        self._stop_event = mp.Event()
        self._command_queue = mp.Queue()


    @property
    def stop_event(self):
        return self._stop_event


    @property
    def command_queue(self):
        return self._command_queue


    def run(self):

        self._disable_keyboard_interrupts()

        execute = self._execute_method

        try:

            # Execute private instance methods in the appropriate order,
            # with appropriate cleanup methods at each step.
            execute('_start_logging', [], logging_available=False)
            execute('_start', ['_stop_logging'])
            execute('_run', ['_stop', '_stop_logging'])
            execute('_stop', ['_stop_logging'])
            execute('_stop_logging', [], logging_available=False)

        except _MethodExecutionError:
            pass


    def _disable_keyboard_interrupts(self):

        print(f'Disabling keyboard interrupts for process "{self.name}".')

        # Disable keyboard interrupts for this process. We want only the
        # main process to receive keyboard interrupts so that it can
        # direct the orderly shutdown of all the other processes.
        try:
            signal.signal(signal.SIGINT, signal.SIG_IGN)
        except Exception as e:
            print(
                f'Attempt to ignore keyboard interrupts at recorder process '
                f'startup raised an exception that will be ignored. As a result, '
                f'keyboard interrupts may not work properly. '
                f'Exception message was: {e}', file=sys.stderr)


    def _execute_method(
            self, method_name, cleanup_method_names, logging_available=True):
        

        def handle_exception(action, e):

            # Create error message.
            message = (
                f'Attempt to {action} recorder process "{self.name}" '
                f'method "{method_name}" unexpectedly raised '
                f'"{type(e).__name__}" exception, so process will now '
                f'exit. Error message was: {e}')
            
            # Log error message.
            if logging_available:
                _logger.error(message)
            else:
                print(message, file=sys.stderr)

            # Execute any specified cleanup methods.
            for cleanup_method_name in cleanup_method_names:
                try:
                    method = getattr(self, cleanup_method_name)
                    method()
                except Exception:
                    break

            raise _MethodExecutionError()


        # Get method.
        try:
            method = getattr(self, method_name)
        except Exception as e:
            handle_exception('get', e)

        # Execute method.
        try:
            method()
        except Exception as e:
            handle_exception('execute', e)


    def _start_logging(self):
        raise NotImplementedError()
    

    def _start(self):
        pass


    def _run(self):

        while not self._stop_event.is_set():

            try:
                command = self._command_queue.get(timeout=1)
            except queue.Empty:
                continue

            # For convenience, allow commands that have no arguments to
            # be enqueued as strings.
            if isinstance(command, str):
                command = Bunch(name=command)

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


    def _stop(self):
        pass


    def _stop_logging(self):

        """
        Stop logging for this process.

        The default implementation of this method performs only the
        logging shutdown needed by producers of log messages, which
        write to the logging queue. It does not perform additional
        logging shutdown needed by the main process, which also reads
        from the logging queue.

        The default implementation of this method assumes that this
        process's logging queue handler is available as the
        `_logging_queue_handler` attribute and that its handle to the
        logging queue is available as the `_logging_queue` attribute.
        Subclasses that use the default implementation should set these
        attributes in their `_start_logging` method.
        """

        # Close logging queue handler.
        logger = logging.getLogger()
        handler = self._logging_queue_handler
        logger.removeHandler(handler)
        handler.close()

        # Close this process's handle to logging queue and wait for
        # queue feeder thread to exit.
        queue = self._logging_queue
        queue.close()
        queue.join_thread()
