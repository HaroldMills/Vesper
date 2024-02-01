import numpy as np

from vesper.recorder.audio_sample_format import AUDIO_SAMPLE_FORMATS
from vesper.tests.test_case import TestCase


TEST_SAMPLE_DTYPES = ('int16', 'int32', 'float32', 'float64')


class AudioSampleFormatTests(TestCase):


    def test_init(self):

        cases = (
            (AUDIO_SAMPLE_FORMATS['int16'], 'int16', 2, -32768, 32767, 32768),
        )

        for case in cases:
            self._test_init(*case)
            
         
    def _test_init(
            self, format, name, sample_size, min_sample, max_sample,
            max_abs_sample):
         
         self.assertEqual(format.name, name)
         self.assertEqual(format.sample_size, sample_size)
         self.assertEqual(format.min_sample, min_sample)
         self.assertEqual(format.max_sample, max_sample)
         self.assertEqual(format.max_abs_sample, max_abs_sample)


    def test_get_raw_sample_data(self):

        samples = np.arange(6).reshape(2, 3)

        cases = (
            (AUDIO_SAMPLE_FORMATS['int16'],
                 np.array([0, 3, 1, 4, 2, 5], dtype='int16').tobytes()),
        )

        for sample_format, expected in cases:
            self._test_get_raw_sample_data(sample_format, samples, expected)


    def _test_get_raw_sample_data(self, format, samples, expected):
        for dtype in TEST_SAMPLE_DTYPES:
            s = samples.astype(dtype)
            actual = format.get_raw_sample_data(s)
            self.assertEqual(actual, expected)


    def test_normalize_samples(self):

        samples = np.arange(6).reshape(2, 3)

        cases = (
            (AUDIO_SAMPLE_FORMATS['int16'], samples.astype('float32') / 32768),
        )

        for sample_format, expected in cases:
            self._test_normalize_samples(sample_format, samples, expected)
        

    def _test_normalize_samples(self, format, samples, expected):
        for dtype in TEST_SAMPLE_DTYPES:
            s = samples.astype(dtype)
            actual = format.normalize_samples(s)
            self.assert_arrays_equal(actual, expected)
