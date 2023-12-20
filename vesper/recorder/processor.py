from vesper.recorder.processor_error import ProcessorError


class Processor:
    

    @staticmethod
    def parse_settings(mapping):
        raise NotImplementedError()
    

    def __init__(self, name, settings, input_info, output_info=None):
        self._name = name
        self._settings = settings
        self._input_info = input_info
        self._output_info = output_info
        self._running = False
    

    @property
    def name(self):

        """the name of this processor, a `str`."""

        return self._name
    

    @property
    def settings(self):

        """
        the settings of this processor, a `Bunch`.

        Many processors are parameterized by *settings*. For example,
        an audio file writer might have settings for the maximum file
        size and the directory to which to write files, and a detector
        might have a detection threshold setting. The settings for
        a processor are gathered into a single `Bunch` object with
        one attribute per setting.
        """

        return self._settings
 
 
    @property
    def input_info(self):

        """
        information about the input items of this processor.
        
        The type of this property varies with the type of processor.
        The value of the property provides information about the input
        items this processor will receive. For example, for an audio
        processor the value might indicate the input channel count and
        sample rate.
        """

        return self._input_info
    

    @property
    def output_info(self):

        """
        information about the output items of this processor.
        
        The type of this property varies with the type of processor.
        The value of the property provides information about the
        output items this processor will produce. For example,
        for an audio processor the value might indicate the output
        channel count and sample rate. For a processor that does
        not produce output, the value of this property should be
        `None`.
        """

        return self._output_info
    

    @property
    def running(self):

        """`True` if and only if this processor is running."""

        return self._running
    

    def start(self):
        if not self._running:
            self._start()
            self._running = True


    def _start(self):
        raise NotImplementedError()
    

    def process(self, input_item):
       
       if not self._running:
           raise ProcessorError(
               f'Attempt to process input with processor "{self.name}" '
               f'that is not running.')
       
       self._process(input_item)
    

    def _process(input_item):
        raise NotImplementedError()
    

    def stop(self):
        if self._running:
            self._stop()
            self._running = False


    def _stop(self):
        raise NotImplementedError()
