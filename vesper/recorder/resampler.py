import logging

import numpy as np
import soxr

from vesper.recorder.processor import Processor
from vesper.recorder.status_table import StatusTable
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_QUALITY = 'HQ'


class Resampler(Processor):


    type_name = 'Resampler'


    @staticmethod
    def parse_settings(settings):

        output_sample_rate = float(settings.get_required('output_sample_rate'))

        quality = settings.get('quality', _DEFAULT_QUALITY)

        if quality not in ('HQ', 'VHQ'):
            raise ValueError(
                f'Unrecognized resampling quality "{quality}". Quality '
                f'must be either "HQ" or "VHQ".')
        
        return Bunch(
            output_sample_rate=output_sample_rate,
            quality=quality)
    

    def __init__(self, name, settings, input_info):

        self._output_sample_rate = settings.output_sample_rate
        self._quality = settings.quality

        self._channel_count = input_info.channel_count
        self._input_sample_rate = input_info.sample_rate

        output_info = Bunch(
            channel_count=self._channel_count,
            sample_rate=self._output_sample_rate)

        super().__init__(name, settings, input_info, output_info)


    @property
    def output_sample_rate(self):
        return self._output_sample_rate
    

    @property
    def quality(self):
        return self._quality
    

    def _start(self):
        self._resampler = soxr.ResampleStream(
            self._input_sample_rate, self._output_sample_rate,
            self._channel_count, 'float32', self._quality)


    def _process(self, input_item):
        
        samples = input_item.samples
        frame_count = input_item.frame_count

        # Truncate input buffer to only samples to be processed and
        # transpose so frame index is first.
        samples = samples[:, :frame_count].transpose()

        # TODO: We never pass `True` as the second argument to
        # `soxr.ResampleStream.resample_chunk`. Perhaps we could make
        # that happen. More generally, there is currently no way to
        # signal to `Processor.process` that the samples it's receiving
        # are final, but there probably should be. Once there is, we
        # may be able to eliminate `Processor.stop`.
        # Resample.
        samples = self._resampler.resample_chunk(samples, False)

        frame_count = samples.shape[0]

        # _logger.info(
        #     f'Resampler._process: {input_frame_count} {output_frame_count}')

        if frame_count == 0:
            return []
        
        else:

            # Transpose samples so channel index is first.
            samples = samples.transpose()
            
            output_item = Bunch(
                samples=samples,
                frame_count=frame_count)

            return [output_item]


    def _stop(self):
        pass


    def get_status_tables(self):

        rows = (
            ('Input Sample Rate (Hz)', str(self._input_sample_rate)),
            ('Output Sample Rate (Hz)', str(self.output_sample_rate)),
            ('Quality', self.quality))

        table = StatusTable(self.name, rows)
        
        return [table]
