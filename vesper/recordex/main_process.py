"""Main recorder process."""


from logging import Formatter, FileHandler, StreamHandler
from logging.handlers import QueueHandler, QueueListener
from threading import Thread
import logging
import multiprocessing as mp
import time

from pyparsing import Path

from vesper.recordex.audio_input_process import AudioInputProcess
from vesper.recordex.recorder_process import RecorderProcess
from vesper.util.bunch import Bunch


_LOG_FILE_NAME = 'Vesper Recorder Log.txt'
_DEFAULT_LOGGING_LEVEL = 'INFO'


_logger = logging.getLogger(__name__)


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

I later asked ChatGPT 5 the following question:

    Could you please explain how the Python Standard Library classes
    logging.handlers.QueueListener and logging.handlers.QueueHandler
    work together to safely log messages from multiple processes? I'm
    particularly interested in any extra threads that are involved,
    ensuring that they terminate gracefully when a program shuts down.

Its response:

    Here’s how QueueHandler and QueueListener work together for safe,
    multi-process logging, and what threads are involved.

    Concept:

    * Child/subprocess side (producer):

      - Attach a logging.handlers.QueueHandler to the process’s root logger.

      - QueueHandler.enqueue() puts LogRecord objects onto a
        multiprocessing.Queue.

      - QueueHandler.prepare() makes the record picklable (formats args,
        converts exc_info, etc.), so it can cross process boundaries.

    * Main process side (consumer):

      - Create the multiprocessing.Queue once in the main process.

      - Start a logging.handlers.QueueListener with that queue and the real
        handlers (FileHandler, StreamHandler, etc.).

      - QueueListener runs a dedicated background thread that pulls records
        from the queue and emits them via the configured handlers.

    Threads involved:

    * In each producer process:

      - multiprocessing.Queue uses a feeder thread to serialize and write
        objects to its pipe. That feeder thread must be allowed to exit
        cleanly.

    * In the main/consumer process:

      - QueueListener starts one background thread (its “monitor” thread)
        that loops on queue.get(), dispatching records to handlers until
        it sees a sentinel and exits.

    Graceful shutdown:

    * Subprocesses (producers):

      - Do not call logging.shutdown().

      - Remove and close the QueueHandler from the process’s root logger.

      - Close and join the process’s end of the multiprocessing.Queue to
        let its feeder thread exit:

            queue.close()
            queue.join_thread()

    * Main process (consumer):

      - Stop the QueueListener to terminate its monitor thread and drain
        remaining records:

            listener.stop()     # posts a sentinel and joins the thread

      - Then flush/close real handlers:

            logging.shutdown()  # optional to call explicitly; it’s also registered via atexit, but explicit is safer in controlled shutdowns)

    Recommended pattern (minimal example):

        import logging
        from logging import Formatter, FileHandler, StreamHandler
        from logging.handlers import QueueHandler, QueueListener
        import multiprocessing as mp
        import atexit

        def setup_main_logging():
            q = mp.Queue()

            console = StreamHandler()
            console.setFormatter(Formatter('%(asctime)s %(processName)s %(levelname)s %(message)s'))

            file = FileHandler('app.log', encoding='utf-8')
            file.setFormatter(Formatter('%(asctime)s %(processName)s %(levelname)s %(message)s'))

            listener = QueueListener(q, console, file)
            listener.start()

            # Ensure listener stops before logging.shutdown runs.
            atexit.register(listener.stop)
            return q, listener

        def setup_child_logging(q, level=logging.INFO):
            root = logging.getLogger()
            root.setLevel(level)
            qh = QueueHandler(q)
            root.addHandler(qh)
            return qh

        def cleanup_child_logging(q, qh):
            root = logging.getLogger()
            try:
                root.removeHandler(qh)
                qh.close()
            finally:
                # Let the feeder thread exit cleanly.
                q.close()
                q.join_thread()

        def worker(q):
            qh = setup_child_logging(q)
            try:
                logging.info('Hello from child')
            finally:
                cleanup_child_logging(q, qh)

        if __name__ == '__main__':
            q, listener = setup_main_logging()

            procs = [mp.Process(target=worker, args=(q,)) for _ in range(2)]
            for p in procs: p.start()
            for p in procs: p.join()

            # Controlled shutdown (optional; atexit will also run):
            listener.stop()
            logging.shutdown()

    Key takeaways:

    * QueueHandler only enqueues records; real formatting/output happens
      in the main process.

    * QueueListener runs one background thread to consume and dispatch
      records.

    * Clean shutdown requires:

      - Children: remove/close QueueHandler, then close/join their queue
        handle (stops feeder threads).

      - Main: listener.stop() (stops monitor thread), then logging.shutdown()
        to flush/close handlers.

    * Relying solely on atexit for logging.shutdown is usually fine,
      but you still must stop the QueueListener explicitly to avoid
      shutdown tracebacks and lost records.

Further questions clarified that if the main process wants to log messages,
it should also use a QueueHandler to send them to the logging queue, and
perform the same cleanup steps for its QueueHandler as child processes.
'''


class MainProcess(RecorderProcess):


    def __init__(self):
        super().__init__('Main')


    def _set_up_logging(self):

        """Set up logging for the main recorder process."""

        self._home_dir_path = Path.cwd()

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


    def _init(self):

        _logger.info(f'Welcome to the Vesper Recorder!')

        # TODO: When we have settings, allow them to override the default
        # logging level.

        self._settings = Bunch()

        self._context = Bunch(
            logging_queue=self._logging_queue,
            logging_level=_DEFAULT_LOGGING_LEVEL)

        self._subprocesses = self._create_and_start_subprocesses()
        self._threads = self._create_and_start_threads()


    def _create_and_start_subprocesses(self):
        audio_input_process = AudioInputProcess(self._settings, self._context)
        audio_input_process.start()
        return [audio_input_process]


    def _create_and_start_threads(self):

        schedule_thread = _ScheduleThread(self)
        schedule_thread.start()

        stop_thread = _StopThread(self)
        stop_thread.start()

        return [schedule_thread, stop_thread]


    def _do_start_recording(self, command):
        for process in reversed(self._subprocesses):
            process.start_recording()


    def _do_stop_recording(self, command):
        for process in self._subprocesses:
            process.stop_recording()


    def _stop(self):

        _logger.info('MainProcess._stop')

        _logger.info('Stopping subprocesses...')
        self._stop_and_join(self._subprocesses)

        _logger.info('Stopping threads...')
        self._stop_and_join(self._threads)

        _logger.info('All subprocesses and threads have stopped.')

        _logger.info('The Vesper Recorder will now exit.')


    def _stop_and_join(self, objects):

        for o in objects:
            o.stop()

        for o in objects:
            o.join()


    def _tear_down_logging(self):

        """
        Tear down logging for the main recorder process.

        The code in this function is modeled after code suggested by
        ChatGPT 5. See notes above.
        """

        # Drain logging queue and stop queue listener monitor thread.
        # Do this first so monitor thread exits.
        self._logging_queue_listener.stop()

        # Get root logger for this process.
        logger = logging.getLogger()

        # Close logging queue handler.
        handler = self._logging_queue_handler
        logger.removeHandler(handler)
        handler.close()

        # Close this process's handle to logging queue so feeder thread
        # exits.
        queue = self._context.logging_queue
        queue.close()
        queue.join_thread()

        # Flush and close stream and file handlers.
        logging.shutdown()


class _ScheduleThread(Thread):


    def __init__(self, main_process):
        super().__init__()
        self._main_process = main_process


    def run(self):
        
        _logger.info('ScheduleThread starting')

        for _ in range(2):

            time.sleep(1)
            self._main_process.start_recording()

            time.sleep(1)
            self._main_process.stop_recording()

        _logger.info('ScheduleThread exiting')


    def stop(self):
        pass
        # _logger.info('ScheduleThread stopping')


class _StopThread(Thread):


    def __init__(self, main_process):
        super().__init__()
        self._main_process = main_process


    def run(self):

        _logger.info('StopThread starting')

        time.sleep(6)
        self._main_process.stop()

        _logger.info('StopThread exiting')


    def stop(self):
        pass
        # _logger.info('StopThread stopping')
