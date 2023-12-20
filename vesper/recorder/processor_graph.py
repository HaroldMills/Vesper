from collections import defaultdict

from vesper.recorder.processor import Processor


_AUDIO_INPUT = 'Audio Input'


class ProcessorGraph(Processor):


    # TODO: How to provide `processor_classes` in some generic way, so
    # this initializer has the same signature as all other processor
    # initializers? This is similar to the question of how to provide
    # station name as default prefix for audio file writers, though
    # the two questions may have different answers.
    def __init__(self, name, settings, input_info, processor_classes):

        super().__init__(name, settings, input_info)
        
        processor_classes = {cls.name: cls for cls in processor_classes}

        self._processors = []
        """
        The processors of this graph.

        The processors must be ordered so that if the output of processor
        A is the input to processor B, A precedes B.
        """

        processors_by_name = {}
        """Map from processor name to processor."""

        self._downstream_processors = defaultdict(list)
        """
        Map from processor name to sequence of immediately downstream
        processors.

        For the purposes of this map, `_AUDIO_INPUT` is considered to
        be a processor name.
        """
        
        for p in settings:

            # Get processor class.
            try:
                cls = processor_classes.get(p.type)
            except KeyError:
                raise ValueError(f'Unrecognized processor type "{p.type}".')
            
            # Get processor input info
            if p.input == _AUDIO_INPUT:
                processor_input_info = input_info
            else:
                try:
                    input_processor = processors_by_name[p.input]
                except KeyError:
                    raise ValueError(
                        f'Unrecognized processor "{p.input}" specified as '
                        f'input to processor "{p.name}".')
                processor_input_info = input_processor.output_info

            # Create processor.
            processor = cls(p.name, p.settings, processor_input_info)

            # Add processor to data structures.
            self._processors.append(processor)
            processors_by_name[processor.name] = processor
            self._downstream_processors[p.input].append(processor)


    def _start(self):
        for p in self._processors:
            p.start()


    def _process(self, input_item):
        self._process_aux([input_item], _AUDIO_INPUT)


    def _process_aux(self, input_items, source_name):

        """Process the specified input items from the specified source."""

        # Get processors that will process input items.
        processors = self._downstream_processors[source_name]

        for processor in processors:

            for input_item in input_items:

                output_items = processor.process(input_item)

                if output_items is not None:

                    processor_name = processor.name

                    for output_item in output_items:
                        self._process_aux(output_item, processor_name)


    def _stop(self):
        for p in self._processors:
            p.stop()
