"""Main recorder process."""


from threading import Thread
import logging
import time

from vesper.recordex.audio_input_process import AudioInputProcess
from vesper.recordex.recorder_process import RecorderProcess


_logger = logging.getLogger(__name__)


class MainProcess(RecorderProcess):


    def __init__(self, settings, context):
        super().__init__('Main', settings, context)


    def _init(self):
        
        _logger.info('MainProcess._init')

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

        _logger.info('Stopping and joining subprocesses...')
        self._stop_and_join(self._subprocesses)

        _logger.info('Stopping and joining threads...')
        self._stop_and_join(self._threads)

        _logger.info('All processes and threads have been stopped and joined.')


    def _stop_and_join(self, objects):

        for o in objects:
            o.stop()

        for o in objects:
            o.join()


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
        _logger.info('ScheduleThread stopping')


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
        _logger.info('StopThread stopping')
