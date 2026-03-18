"""
The main module of the Vesper Recorder.

This module runs in the Vesper Recorder's main process. After some
initialization it starts the *recorder process*, which in turn starts
all of the other processes of the recorder, including its audio input,
audio processing, and sidecar processes. The main process handles
keyboard interrupts for the recorder and directs the orderly shutdown
of all of the other recorder processes.

Keyboard Interrupt Handling
---------------------------
The Vesper Recorder uses this module as part of a strategy to ensure
that only the main process receives keyboard interrupts. We want this
so that the main process can direct the orderly shutdown of all the
other processes.

The strategy we have adopted is:

1. Disable keyboard interrupts first thing in every recorder process by
   importing this module first thing in the process's main module. This
   disables keyboard interrupts as soon as possible during the import
   phase of the module. The modules that import this module include the
   main process module `vesper_recorder.py`,the recorder process module
   `recorder_process.py`, the audio process modules
   `audio_input_process.py` and `audio_processing_process.py`, and all
   sidecar process modules.

2. Re-enable keyboard interrupts in the main process after some
   initialization.

Note that this strategy leaves the recorder unresponsive to keyboard
interrupts during the first part of the initialization of the main
process. This is not ideal, but I don't think it's a big problem since
the initialization is usually pretty quick.

To try to make the recorder responsive to keyboard interrupts during
more of the main process initialization, I tried to find a way to
disable keyboard interrupts only in non-main processes, but did not
find anything that seemed like it would work reliably across platforms.
In particular, I did not find a way to reliably determine during the
module import phase whether or not code is running in the main process.
One possibility I tried was to check to see if `mp.parent_process()` is
`None`. That didn't work, however, since `mp.parent_process()` is always
`None` during the module import phase of a process, regardless of whether
or not the process is the main process. Another possibility I tried was
to check to see if the process name `mp.current_process().name` is
`"MainProcess"`. It appears that that would work on macOS and Windows 10,
but it seems brittle to me since I don't know of any guarantee that the
main process will have that name. In the interest of robustness, I
decided to go with the strategy described above.

At one point during the development of the recorder, an LLM (I don't
remember which one) suggested that disabling keyboard interrupts during
the import phase at the top of the main process module `vesper_recorder`
would suffice
to disable keyboard interrupts in *all* Vesper Recorder processes,
since that module is automatically imported first thing in all of the
processes. I tried that, and found that while it worked on macOS, it
did not work on Windows 10: for whatever reason, the main module is
*not*  imported first thing in all processes on Windows 10. Hence we
import this module at the tops of all recorder process modules, and
not just the main process module.
"""


# TODO: Augment main process module docstring to describe Vesper
# Recorder software in detail, including its process structure, process
# start method and lifecycle, keyboard interrupt handling, logging, and
# settings.


# Disable keyboard interrupts for this process. The `VesperRecorder`
# object created by the `main` function will re-enable them later. See
# the `vesper.recordex.keyboard_interrupt_disabler` module docstring
# for a detailed discussion of Vesper Recorder keyboard interrupt
# handling.
import vesper.recordex.keyboard_interrupt_disabler

from logging import Formatter, FileHandler, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
import logging
import multiprocessing as mp
import signal
import threading

from vesper.recordex import __version__
from vesper.recordex.lifecycle_executor import LifecycleExecutor

# Note that this import will also disable keyboard interrupts in the main
# process, in addition to the above `keyboard_interrupt_disabler` import.
# We choose not to rely on that, however, and to make the disablement
# explicit.
from vesper.recordex.recorder_process import RecorderProcess

import vesper.recordex.setting_utils as setting_utils


_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_DEFAULT_LOGGING_LEVEL = 'INFO'
_SETTING_FILE_NAME = 'Vesper Recorder Settings.yaml'


_logger = logging.getLogger(__name__)


def main():
    recorder = VesperRecorder()
    recorder.run()


class VesperRecorder:


    def __init__(self):

        self._home_dir_path = Path.cwd()

        # Create event that is set if and only if we have received a
        # keyboard interrupt.
        self._keyboard_interrupt_event = threading.Event()


    def run(self):

        lifecycle = (
            ('_configure_multiprocessing', None, None),
            ('_configure_keyboard_interrupts', None, None),
            ('_start_logging', None, None),
            ('_run', _logger, '_stop_logging'),
            ('_stop_logging', None, None))
        
        executor = LifecycleExecutor(self, 'VesperRecorder', lifecycle)
        executor.execute_lifecycle()



    def _configure_multiprocessing(self):

        # Use the `spawn` multiprocessing start method on all platforms.
        # As of Python 3.12, this is the default for Windows and macOS
        # but not for POSIX. On POSIX the default start method is `fork`,
        # which is fast but copies more parent process state to the child
        # process than we need or want. The extra state can cause problems.
        # For example, in an earlier version of the recorder's multiprocess
        # logging system it caused some log messages to be duplicated on
        # POSIX.
        mp.set_start_method('spawn')


    def _configure_keyboard_interrupts(self):

        def handle_keyboard_interrupt(signal_num, frame):
            self._keyboard_interrupt_event.set()

        signal.signal(signal.SIGINT, handle_keyboard_interrupt)


    def _start_logging(self):

        """
        Start logging for the main process.

        This starts logging for the main process both as a producer of log
        messages and as the manager of the multiprocess logging queue.
        """

        # Create multiprocess logging queue for all processes to write
        # messages to. The messages are handled by the queue listener
        # created below.
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

        # Set logging level to default for now. We will update the level
        # after parsing the recording setting file if it specifies a
        # different level.
        self._set_logging_level(_DEFAULT_LOGGING_LEVEL)

        # Add handler to root logger that writes all log messages to the
        # recorder's logging queue.
        logger = logging.getLogger()
        self._logging_queue_handler = QueueHandler(self._logging_queue)
        logger.addHandler(self._logging_queue_handler)


    def _set_logging_level(self, level):

        # Set level on root logger of this process.
        logger = logging.getLogger()
        logger.setLevel(level)

        self._logging_level = level


    def _run(self):
        self._log_welcome_message()
        self._parse_setting_file()
        self._log_home_page_message()
        self._update_logging_level()
        self._run_recorder_process()
        self._log_exit_message()


    def _log_welcome_message(self):
        _logger.info(f'Welcome to the Vesper Recorder!')
        _logger.info(f'Recorder version number is {__version__}.')


    def _parse_setting_file(self):

        setting_file_path = self._home_dir_path / _SETTING_FILE_NAME

        _logger.info(
            f'Reading recorder settings from file "{setting_file_path}"...')
        
        try:
            self._settings = \
                setting_utils.parse_setting_file(setting_file_path)
            
        except Exception as e:
            _logger.error(str(e))
            raise Exception(
                'Could not parse recorder setting file. '
                'See previous log message for details.')


    def _log_home_page_message(self):
        _logger.info(
            f'Recorder home page URL is '
            f'"http://localhost:{self._settings.server_port_num}".')
        

    def _update_logging_level(self):

        """
        Update logging level if `logging_level` setting is present and
        differs from current level.
        """

        logging_level = self._settings.logging_level

        if logging_level is not None and logging_level != self._logging_level:

            _logger.info(
                f'Setting recorder logging level to setting file '
                f'value "{logging_level}"...')
            
            self._set_logging_level(logging_level)
            

    def _run_recorder_process(self):

        # Create and start recorder process.
        recorder_process = RecorderProcess(
            self._settings, self._logging_level, self._logging_queue)
        recorder_process.start()

        try:
            
            while recorder_process.is_alive():
                
                # Check for keyboard interrupt periodically.
                if self._keyboard_interrupt_event.is_set():
                    self._log_keyboard_interrupt_message()
                    break
                
                recorder_process.join(timeout=1)
        
        except KeyboardInterrupt:
            # keyboard interrupt delivered as `KeyboardInterrupt` exception
            # instead of via call to `handle_keyboard_interrupt`

            self._log_keyboard_interrupt_message()

            # Set keyboard interrupt event, even if nobody will use it, to
            # maintain the invariant that it is set if and only if we have
            # received a keyboard interrupt.
            self._keyboard_interrupt_event.set()
        
        finally:
            
            if recorder_process.is_alive():
                # recorder process is still running

                try:

                    # Tell recorder process to stop.
                    recorder_process.stop_event.set()

                finally:

                    # Wait for recorder process to stop.
                    recorder_process.join()


    def _log_keyboard_interrupt_message(self):
        _logger.info(
            'Main process received keyboard interrupt. '
            'The Vesper Recorder will now shut down.')


    def _log_exit_message(self):
        _logger.info('The Vesper Recorder will now exit.')


    def _stop_logging(self):

        """
        Stop logging for the main process.

        This stops logging for the main process both as a producer of
        log messages and as the manager of the multiprocess logging queue.
        """

        # Note that this method operates on the logging queue handler,
        # the logging queue listener, and the logging queue in the
        # reverse order in which the `_start_logging` method operates
        # on them.
        
        # Close logging queue handler.
        logger = logging.getLogger()
        handler = self._logging_queue_handler
        logger.removeHandler(handler)
        handler.close()

        # Drain logging queue and stop queue listener monitor thread.
        self._logging_queue_listener.stop()

        # Close this process's handle to logging queue and wait for
        # queue feeder thread to exit.
        queue = self._logging_queue
        queue.close()
        queue.join_thread()

        # Flush and close stream and file handlers.
        logging.shutdown()


if __name__ == '__main__':
    main()
