from logging.handlers import QueueHandler
from multiprocessing import Process
import logging

from vesper.util.bunch import Bunch
import vesper.recorder.error_utils as error_utils



# TODO: Consider using command queues for all application processes and
# threads. Also consider using bunches for the commands. But note that
# in some cases it might be advantageous to use a more language-agnostic
# means of communication, such as HTTP or WebSockets. It would be nice,
# for example, if the same detector programs that the Vesper Server
# interacts with could also be used by the Vesper Recorder.


class Sidecar(Process):


    type_name = None
    """
    The name of this sidecar type. Subclasses must override this attribute.
    """


    @staticmethod
    def parse_settings(settings):
        return Bunch()
    

    def __init__(self, name, settings, context):
        super().__init__(name=name)
        self._settings = settings
        self._context = context


    @property
    def settings(self):
        return self._settings
    

    @property
    def context(self):
        return self._context
    

    def run(self):

        try:
            self._configure_logging()
            self._run()

        except KeyboardInterrupt:
            pass

        except Exception:
            error_utils.handle_top_level_exception('S3 file uploader sidecar')


    def _configure_logging(self):
        
        """
        Configures logging for this sidecar.

        This method is intended to be called by the `run` method of
        subclasses. It configures logging according to the `logging_level`
        and `logging_queue` attributes of the sidecar's `context` property.
        """

        # Get the root logger for this process.
        logger = logging.getLogger()

        # Add handler to root logger that writes all log messages to
        # the recorder's logging queue.
        handler = QueueHandler(self._context.logging_queue)
        logger.addHandler(handler)

        # Set logging level for this process.
        logger.setLevel(self._context.logging_level)


    def _run(self):

        """
        Implements the run loop of this sidecar.

        A sidecar's run loop reads and executes commands from the sidecar's
        command queue.
        """

        raise NotImplementedError()
    

    def recording_will_start(self):
        pass


    def recording_did_start(self):
        pass


    def recording_will_stop(self):
        pass


    def recording_did_stop(self):
        pass


    def stop(self):
        pass


    def get_status_tables(self):
        
        """
        Gets a list of `StatusTable` objects to display for this sidecar.
        """

        raise NotImplementedError()
