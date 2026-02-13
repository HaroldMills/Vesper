"""
Base class for all recorder processes, including both the main process and
its subprocesses.
"""


import logging
import multiprocessing as mp
import queue
import sys

from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


# TODO: Document recorder processes, including lifecycle phases (logging
# start, start, command execution, stop, and logging stop)
# command queue, and stop event.

# TODO: Consider supporting two kinds of stop, quick and leisurely.
# A leisurely stop will execute all commands that were queued before the
# stop was requested. A quick stop will finish executing the current
# command (if there is one) and then ignore any others that are in the
# queue. We have implemented only the quick stop below. The leisurely
# stop could be implemented by stopping with a command instead of an
# event. If you want to offer both options, though, use an event and
# a flag indicating which type of stop is desired.

# TODO: Make the enqueueing of commands by one process for another more
# explicit. In particular, do not hide the enqueueing of commands in
# methods of the classes that receive them. Whenever one process will
# send commands to another, pass the receiving process's command queue
# to the sending process's initializer and have the sending process
# enqueue commands directly to the queue. This will make it more clear
# who sends commands to whom and what commands they send.

# TODO: Make setting the stop event of one process by another more
# explicit. Whenever one process will stop another, pass the relevant
# stop event to the stopping process's initializer and have the stopping
# process set the event directly. This will make it more clear who stops
# whom and when.

# TODO: Consider eliminating the recorder subprocess `context` initializer
# argument. I believe it may currently only be used to pass logging
# configuration, which might better be passed more explicitly.


class _MethodExecutionError(Exception):
    pass


class RecorderProcess(mp.Process):


    def __init__(self, name):
        super().__init__(name=name)
        self._command_queue = mp.Queue()
        self._stop_event = mp.Event()


    @property
    def command_queue(self):
        return self._command_queue
    

    @property
    def stop_event(self):
        return self._stop_event


    def run(self):

        execute = self._execute_method

        try:

            # Execute private instance methods in the appropriate order,
            # with appropriate cleanup methods at each step.
            execute('_start_logging', [], logging_available=False)
            execute('_start', ['_stop_logging'])
            execute('_execute_commands', ['_stop', '_stop_logging'])
            execute('_stop', ['_stop_logging'])
            execute('_stop_logging', [], logging_available=False)

        except _MethodExecutionError:
            pass


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


    def _execute_commands(self):

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
