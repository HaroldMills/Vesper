import logging

import numpy as np
import soxr

from vesper.recorder.processor import Processor
from vesper.util.bunch import Bunch


_logger = logging.getLogger(__name__)


_DEFAULT_QUALITY = 'HQ'


class Resampler(Processor):


    name = 'Resampler'


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
        
        # Get NumPy sample array.
        input = np.frombuffer(input_item.samples, dtype=np.int16)
        
        # Make sample array 2D. Compute frame count from sample array
        # length rather than using `input_item.frame_count`, since the latter
        # may be less than the sample array capacity.
        input_frame_count = len(input) // self._channel_count
        input = input.reshape((input_frame_count, self._channel_count))

        # Make sample array `float32` to avoid arithmetic overflow in
        # subsequent processing.
        input = input.astype(np.float32)

        # TODO: We never pass `True` as the second argument to
        # `soxr.ResampleStream.resample_chunk`. Perhaps we could make
        # that happen. More generally, there is currently no way to
        # signal to `Processor.process` that the samples it's receiving
        # are final, but there probably should be. Once there is, we
        # may be able to eliminate `Processor.stop`.
        output = self._resampler.resample_chunk(input, False)

        output_frame_count = output.shape[0]

        # _logger.info(
        #     f'Resampler._process: {input_frame_count} {output_frame_count}')

        if output_frame_count == 0:
            return []
        
        else:

            # Round and clip output to 16-bit sample range.
            output = np.clip(np.round(output), -32768, 32767)

            output = output.astype(np.int16).tobytes()

            output_item = Bunch(
                samples=output,
                frame_count=output_frame_count)

            return [output_item]


    def _stop(self):
        pass


    def get_status_tables(self):

        rows = (
            ('Output Sample Rate', str(self.output_sample_rate)),
            ('Quality', self.quality))

        table = Bunch(title=self.name, rows=rows)
        
        return [table]
