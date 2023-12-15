from vesper.recorder.processor_error import ProcessorError
import vesper.util.time_utils as time_utils


class Processor:
    

    def __init__(self, name, channel_count, input_sample_rate, settings):

        self._name = name
        self._channel_count = channel_count
        self._input_sample_rate = input_sample_rate
        self._settings = settings

        self._running = False
        self._start_time = None
    

    @property
    def name(self):
        return self._name
    

    @property
    def channel_count(self):
        return self._channel_count
    

    @property
    def input_sample_rate(self):
        return self._input_sample_rate
    

    @property
    def settings(self):
        return self._settings
 
 
    @property
    def running(self):
        return self._running
    

    @property
    def start_time(self):
        return self._start_time
    

    def start(self):

        if not self._running:

            self._start_time = time_utils.get_utc_now()

            self._start()

            self._running = True


    def _start(self):
        raise NotImplementedError()
    

    def process(self, samples, frame_count):
       
       if not self._running:
           raise ProcessorError(
               f'Attempt to process data with processor "{self.name}" '
               f'that is not running.')
       
       self._process(samples, frame_count)
    

    def _process():
        raise NotImplementedError()
    

    def stop(self):

        if self._running:

            self._stop()

            self._running = False
            self._start_time = None


    def _stop(self):
        raise NotImplementedError()
