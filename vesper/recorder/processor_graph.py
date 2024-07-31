from collections import defaultdict
import itertools
import logging

from vesper.recorder.processor import Processor


_logger = logging.getLogger(__name__)


_AUDIO_INPUT = 'Audio Input'


class ProcessorGraph(Processor):


    def __init__(self, name, settings, context, input_info):

        super().__init__(name, settings, context, input_info)
        
        processor_classes = \
            {cls.type_name: cls for cls in context.processor_classes}

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
            processor = cls(p.name, p.settings, context, processor_input_info)

            # Add processor to data structures.
            self._processors.append(processor)
            processors_by_name[processor.name] = processor
            self._downstream_processors[p.input].append(processor)


    def _start(self):
        for p in self._processors:
            p.start()


    def _process(self, input_item, finished):
        self._process_aux([input_item], _AUDIO_INPUT, finished)


    def _process_aux(self, input_items, source_name, finished):

        """Process the specified input items from the specified source."""

        # _logger.info(f'ProcessorGraph._process_aux {source_name}')

        # Get processors that will process output items as input items.
        processors = self._downstream_processors[source_name]

        for processor in processors:

            item_count = len(input_items)

            for i, input_item in enumerate(input_items):

                finished_ =  finished and i == item_count - 1

                output_items = processor.process(input_item, finished_)

                if output_items is not None and len(output_items) != 0:
                    self._process_aux(output_items, processor.name, finished_)


    def get_status_tables(self):
        chain = itertools.chain.from_iterable
        table_lists = [p.get_status_tables() for p in self._processors]
        return list(chain(table_lists))