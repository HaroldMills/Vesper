"""The main function of the Vesper Recorder."""


from logging import Formatter, FileHandler, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
import logging
import multiprocessing as mp
import time

from vesper.recordex.main_process import MainProcess
from vesper.util.bunch import Bunch


# TODO: Consider supporting two kinds of stop, quick and leisurely.
# A leisurely stop will execute all commands that were queued before the
# stop was requested. A quick stop will finish executing the current
# command (if there is one) and then ignore any others that are in the
# queue. We have implemented only the quick stop below. The leisurely
# stop could be implemented by stopping with a command instead of an
# event. If you want to offer both options, though, use an event and
# a flag indicating which type of stop is desired.


'''
Tasks:

+ Move process classes to their own modules.

* Make `_main` a minimal function that just creates, starts, and joins
  the main process. Call the process that runs `_main` the *bootstrap
  process*. Do not do any logging in the bootstrap process.

* Add `_start_logging` and `_stop_logging` methods to `RecorderProcess`.
  Call the methods from the `run` method. The default implementations of
  the methods raise `NotImplementedError`.

* Implement `_start_logging` and `_stop_logging` for `MainProcess`.

* Create a `Subprocess` class that inherits from `RecorderProcess`.
  Implement `_start_logging` and `_stop_logging` for subprocesses in it.

* Modify `AudioInputProcess` to inherit from `Subprocess`.

* Add Ctrl-C interrupts. Test on macOS, Windows, and Raspberry Pi OS.

* Add some very simple YAML settings. Parse them so that if parsing fails
  you see a nice error message indicating where the problem is. Test on
  macOS, Windows, and Raspberry Pi OS.

* Add settings parsing for real.

* Add audio input.

* Add audio processor process.

* Add schedule thread.

* Add S3 file uploader sidecar.

* Add WAVE to FLAC converter sidecar.

* Add UI thread.

* Add start/stop button to UI.

* Add dynamic level meter to UI.
'''


'''
Logging Shutdown
----------------

In an earlier version of the Vesper Recorder, I had some logging problems
at shutdown. Some messages were sometimes not logged, and I also often saw
an exception message like the following at shutdown:

    Exception in thread Thread-6 (_monitor):
    Traceback (most recent call last):
        File "/Users/harold/miniconda3/envs/vesper-dev/lib/python3.11/threading.py", line 1045, in _bootstrap_inner. 

One of my main goals in the a newere version of the recorder is to handle
recorder shutdown better, for example by stopping and joining all
subprocesses and threads. With this in mind, I asked ChatGPT 5 (via GitHub
Copilot in VS Code) about the above error message, and it responded (in part):

    It’s the logging QueueListener’s background thread dying during
    interpreter shutdown. You start a QueueListener but never stop it.
    Its internal _monitor thread is still reading from the
    multiprocessing.Queue when handlers/objects are being torn down,
    so you see a traceback like “Exception in thread Thread-… (_monitor)”.

I then asked the followup question:
    
    I'm writing a Python application whose main process will create
    multiple subprocesses. Each of the subprocesses will use the logging
    module of the Python Standard Library to perform logging, sending log
    messages to a multiprocessing logging queue managed by the main process.
    Do the subprocesses need to call the logging.shutdown function when they
    complete, say by registering an appropriate function via the atexit
    module, or does only the main process need to call logging.shutdown?

and got this response:

    Short answer: only the main process should call logging.shutdown.
    Subprocesses should not.

    Guidance:

    * Main process

      - Owns the QueueListener and any real handlers (file/stream).

      - Stop the listener and then call logging.shutdown after all
        children exit.
        
    * Subprocesses

      - Use only a QueueHandler pointing at the shared multiprocessing.Queue.

      - Do not stop the listener and do not call logging.shutdown (it’s
        unnecessary and can be misleading).

      - Clean up per-process resources: remove/close the QueueHandler and
        close/join the process’s end of the queue so its feeder thread exits.

Example cleanup:


    # child process cleanup
    import logging

    def cleanup_child_logging(logging_queue, queue_handler):
        root = logging.getLogger()
        try:
            root.removeHandler(queue_handler)
            queue_handler.close()
        finally:
            # close this process's handle to the queue so the feeder thread exits
            logging_queue.close()
            logging_queue.join_thread()


    # main process cleanup
    import logging
    from logging.handlers import QueueListener

    def cleanup_main(listener: QueueListener):
        try:
            listener.stop()   # drains queue and stops background thread
        finally:
            logging.shutdown()  # flush/close file/stream handlers


    Key points:

    * Don’t call listener.stop() from children.

    * Closing/joining the child’s queue handle prevents shutdown tracebacks
      from feeder/monitor threads.
'''


_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_DEFAULT_LOGGING_LEVEL = 'INFO'


_logger = logging.getLogger(__name__)


def _main():
    home_dir_path = Path.cwd()
    _create_and_run_recorder(home_dir_path)
    

def _create_and_run_recorder(home_dir_path):
    
    logging_queue = _configure_logging(home_dir_path)
    
    _logger.info(f'Welcome to the Vesper Recorder!')

    # TODO: When we have settings, allow them to override the default
    # logging level.

    context = Bunch(
        logging_queue=logging_queue,
        logging_level=_DEFAULT_LOGGING_LEVEL,
    )

    main_process = MainProcess(None, context)
    main_process.start()
    main_process.join()

    _logger.info('The Vesper Recorder will now exit.')

    logging.shutdown()


def _configure_logging(home_dir_path):

    # Create logging queue for all recorder processes to write messages
    # to. The messages are handled by the queue listener created below.
    logging_queue = mp.Queue()

    # Create handler that writes log messages to stderr.
    stderr_handler = StreamHandler()
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    stderr_handler.setFormatter(formatter)
    
    # Create handler that appends messages to log file.
    log_file_path = home_dir_path / _LOG_FILE_NAME
    file_handler = FileHandler(log_file_path)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    # Create logging queue listener that reads messages from the queue
    # and logs them.
    listener = QueueListener(logging_queue, stderr_handler, file_handler)
    listener.start()

    # TODO: Stop queue listener when recorder quits.

    # Get the root logger for the main recorder process.
    logger = logging.getLogger()

    # Add handler to root logger that writes all log messages to the
    # recorder's logging queue.
    handler = QueueHandler(logging_queue)
    logger.addHandler(handler)

    # Set logging level to default for now. The level will be updated
    # after the recorder settings file is parsed in case it is specified
    # there.
    logger.setLevel(_DEFAULT_LOGGING_LEVEL)

    return logging_queue


if __name__ == '__main__':
    _main()
