import numpy as np

from vesper.tests.test_case import TestCase
import vesper.util.time_frequency_analysis_utils as tfa_utils


'''
TODO: Add test cases for which window size differs from DFT size,
and for which window is not rectangular.
'''

'''
TODO: Given that we need to test FFTs and spectrograms implemented
in various programming languages, it might make sense to prepare a
set of test cases in a language-portable format like JSON that can
be used by test code in the different languages.
'''


class TimeFrequencyAnalysisUtilsTests(TestCase):


    def test_get_dft_analysis_data(self):

        cases = [
            (1000, 4, None, 4, [0, 250, 500])
        ]

        for sample_rate, window_size, dft_size, expected_dft_size, \
                expected_freqs in cases:

            expected_freqs = np.array(expected_freqs)

            actual_dft_size, actual_freqs = tfa_utils.get_dft_analysis_data(
                sample_rate, window_size, dft_size)

            self.assertEqual(actual_dft_size, expected_dft_size)
            self.assertTrue(np.array_equal(actual_freqs, expected_freqs))


    def test_get_dft_size(self):

        cases = [
            (1, 1),
            (2, 2),
            (3, 4),
            (4, 4),
            (5, 8),
            (6, 8),
            (7, 8),
            (8, 8),
            (9, 16)
        ]

        for window_size, expected in cases:
            actual = tfa_utils.get_dft_size(window_size)
            self.assertEqual(actual, expected)


    def test_get_dft_freqs(self):

        cases = [
            (1000, 1, [0]),
            (1000, 2, [0, 500]),
            (1000, 4, [0, 250, 500]),
            (2000, 8, [0, 250, 500, 750, 1000])
        ]

        for sample_rate, dft_size, expected in cases:
            expected = np.array(expected)
            actual = tfa_utils.get_dft_freqs(sample_rate, dft_size)
            self.assertTrue(np.array_equal(actual, expected))


    def test_get_dft_bin_num(self):
        
        cases = [
            ((0, 8000, 8), 0),
            ((4000, 8000, 8), 4),
            ((1000, 8000, 8), 1),
            ((499, 8000, 8), 0),
            ((501, 8000, 8), 1),
            ((11024.5, 22050., 8), 4)
        ]
        
        for args, expected in cases:
            actual = tfa_utils.get_dft_bin_num(*args)
            self.assertEqual(actual, expected)
        
        
    def test_get_num_analysis_records(self):

        cases = [
            (0, 8, 4, 0),
            (8, 8, 4, 1),
            (16, 8, 4, 3),
            (17, 8, 4, 3),
            (18, 8, 4, 3),
            (19, 8, 4, 3),
            (20, 8, 4, 4),
            (20, 8, 3, 5),
            (21, 8, 3, 5),
            (22, 8, 3, 5),
            (23, 8, 3, 6)
        ]

        for num_samples, window_size, hop_size, expected in cases:
            actual = tfa_utils.get_num_analysis_records(
                num_samples, window_size, hop_size)
            self.assertEqual(actual, expected)


    def test_get_num_analysis_records_errors(self):

        cases = [

            # record size zero
            (0, 0, 1),

            # hop size zero
            (0, 1, 0),

            # hop size exceeds record size
            (0, 1, 2)

        ]

        for args in cases:
            self.assert_raises(
                ValueError, tfa_utils.get_num_analysis_records, *args)


    def test_get_analysis_records_1d(self):

        """Tests `get_analysis_records` with 1-dimensional input."""

        samples = np.arange(8)

        cases = [

            # record size and hop size equal
            (1, 1, [[0], [1], [2], [3], [4], [5], [6], [7]]),
            (2, 2, [[0, 1], [2, 3], [4, 5], [6, 7]]),
            (3, 3, [[0, 1, 2], [3, 4, 5]]),
            (4, 4, [[0, 1, 2, 3], [4, 5, 6, 7]]),
            (5, 5, [[0, 1, 2, 3, 4]]),
            (8, 8, [[0, 1, 2, 3, 4, 5, 6, 7]]),

            # record size and hop size not equal
            (2, 1, [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7]]),
            (3, 2, [[0, 1, 2], [2, 3, 4], [4, 5, 6]]),
            (4, 2, [[0, 1, 2, 3], [2, 3, 4, 5], [4, 5, 6, 7]]),
            (4, 3, [[0, 1, 2, 3], [3, 4, 5, 6]]),

        ]

        self._test_get_analysis_records(samples, cases)


    def _test_get_analysis_records(self, samples, cases):

        for record_size, hop_size, expected in cases:

            expected = np.array(expected)

            actual = tfa_utils._get_analysis_records(
                samples, record_size, hop_size)

            self.assert_arrays_equal(actual, expected)


    def test_get_analysis_records_2d(self):

        """Tests `get_analysis_records` with 2-dimensional input."""

        samples = np.arange(8).reshape((2, 4))

        cases = [

            # record size and hop size equal
            (1, 1, [[[0], [1], [2], [3]], [[4], [5], [6], [7]]]),
            (2, 2, [[[0, 1], [2, 3]], [[4, 5], [6, 7]]]),
            (3, 3, [[[0, 1, 2]], [[4, 5, 6]]]),
            (4, 4, [[[0, 1, 2, 3]], [[4, 5, 6, 7]]]),

            # record size and hop size not equal
            (2, 1, [[[0, 1], [1, 2], [2, 3]], [[4, 5], [5, 6], [6, 7]]]),
            (3, 1, [[[0, 1, 2], [1, 2, 3]], [[4, 5, 6], [5, 6, 7]]]),
            (3, 2, [[[0, 1, 2]], [[4, 5, 6]]])

        ]

        self._test_get_analysis_records(samples, cases)


    def test_compute_spectrogram(self):

        # This tests that our spectrogram function produces the
        # expected output for an input comprising a single channel
        # with a single window's worth of cosine samples. We use
        # a rectangular window so the expected output spectrum has
        # a particularly simple form.

        for num_channels in [1, 2]:

            for dft_size in [1, 2, 4, 8, 16]:

                if dft_size == 1:
                    hop_sizes = [1]
                else:
                    hop_sizes = [dft_size // 2, dft_size]

                for hop_size in hop_sizes:

                    for bin_num in range(dft_size // 2 + 1):

                        self._test_compute_spectrogram(
                            num_channels, dft_size, hop_size, bin_num)


    def _test_compute_spectrogram(
            self, num_channels, dft_size, hop_size, bin_num):

        num_samples = dft_size * 2
        samples = self._create_test_signal(
            num_channels, num_samples, dft_size, bin_num)

        window = np.ones(dft_size)

        spectra = tfa_utils.compute_spectrogram(
            samples, window, hop_size, dft_size)

        expected = self._get_expected_spectra(
            num_channels, num_samples, hop_size, dft_size, bin_num)

        self.assertTrue(np.allclose(spectra, expected))


    def _create_test_signal(
            self, num_channels, num_samples, dft_size, bin_num):

        phase_factor = 2 * np.pi * bin_num / dft_size
        samples = np.cos(phase_factor * np.arange(num_samples))

        if num_channels == 2:
            samples = np.stack((samples, np.ones(num_samples)))

        return samples


    def _get_expected_spectra(
            self, num_channels, num_samples, hop_size, dft_size, bin_num):

        num_spectra = tfa_utils.get_num_analysis_records(
            num_samples, dft_size, hop_size)

        spectrum = self._get_expected_spectrum(dft_size, bin_num)
        spectra = np.ones((num_spectra, 1)) * spectrum

        if num_channels == 2:
            spectrum = self._get_expected_spectrum(dft_size, 0)
            spectra_1 = np.ones((num_spectra, 1)) * spectrum
            spectra = np.stack((spectra, spectra_1))

        return spectra


    def _get_expected_spectrum(self, dft_size, bin_num):
        num_bins = dft_size // 2 + 1
        spectrum = np.zeros(num_bins)
        spectrum[bin_num] = dft_size ** 2
        if bin_num != 0 and bin_num != num_bins - 1:
            spectrum[bin_num] /= 4
        return spectrum.reshape((1, len(spectrum)))


    def test_scale_spectrogram(self):

        cases = [

            # empty
            (np.zeros((0, 1)), np.zeros((0, 1))),
            (np.zeros((0, 3)), np.zeros((0, 3))),

            # mono
            ([[1], [2]], [[1], [2]]),
            ([[1, 2], [3, 4]], [[.5, 1], [1.5, 2]]),
            ([[1, 2, 3]], [[.25, 1, .75]]),

            # stereo
            ([[[1], [2]], [[3], [4]]], [[[1], [2]], [[3], [4]]]),
            ([[[1, 2], [3, 4]], [[5, 6], [7, 8]]],
             [[[.5, 1], [1.5, 2]], [[2.5, 3], [3.5, 4]]]),
            ([[[1, 2, 3]], [[4, 5, 6]]], [[[.25, 1, .75]], [[1, 2.5, 1.5]]])

        ]

        for spectra, expected in cases:

            spectra = np.array(spectra, dtype='float64')
            expected = np.array(expected, dtype='float64')

            self._test_op(expected, tfa_utils.scale_spectrogram, spectra)


    def _test_op(self, expected, op, input, *args, **kwargs):

        # out of place, result allocated by op
        actual = op(input, *args, **kwargs)
        self.assertFalse(actual is input)
        self.assert_arrays_equal(actual, expected)

        # out of place, result preallocated
        actual = np.zeros_like(expected)
        kwargs_ = dict(kwargs, out=actual)
        actual = op(input, *args, **kwargs_)
        self.assertFalse(actual is input)
        self.assert_arrays_equal(actual, expected)

        # in place
        kwargs_ = dict(kwargs, out=input)
        actual = op(input, *args, **kwargs_)
        self.assertTrue(actual is input)
        self.assert_arrays_equal(actual, expected)


    def test_linear_to_log(self):

        minus_infinity = tfa_utils.SMALL_POWER_DB

        cases = [

            # empty
            (np.zeros((0, 1)), np.zeros((0, 1))),
            (np.zeros((0, 3)), np.zeros((0, 3))),

            # mono
            ([[0], [1], [10]], [[minus_infinity], [0], [10]]),
            ([[0, 1], [1, 10]], [[minus_infinity, 0], [0, 10]]),

            # stereo
            ([[[0, 1], [1, 10]], [[1, 10], [10, 100]]],
             [[[minus_infinity, 0], [0, 10]], [[0, 10], [10, 20]]])

        ]

        # default reference power
        for spectra, expected in cases:
            spectra = np.array(spectra, dtype='float64')
            expected = np.array(expected, dtype='float64')
            self._test_op(expected, tfa_utils.linear_to_log, spectra)

        # explicit reference power
        reference_power = 10
        reference_power_db = 10 * np.log10(reference_power)
        for spectra, expected in cases:
            spectra = np.array(spectra, dtype='float64')
            expected = np.array(expected, dtype='float64')
            expected[expected != minus_infinity] -= reference_power_db
            self._test_op(
                expected, tfa_utils.linear_to_log, spectra, reference_power)


    def test_log_to_linear(self):

        cases = [

            # empty
            (np.zeros((0, 1)), np.zeros((0, 1))),
            (np.zeros((0, 3)), np.zeros((0, 3))),

            # mono
            ([[-10], [0], [10]], [[.1], [1], [10]]),
            ([[-10, 0], [0, 10]], [[.1, 1], [1, 10]]),

            # stereo
            ([[[-10, 0], [0, 10]], [[0, 10], [10, 20]]],
             [[[.1, 1], [1, 10]], [[1, 10], [10, 100]]])

        ]

        # default reference power
        for spectra, expected in cases:
            spectra = np.array(spectra, dtype='float64')
            expected = np.array(expected, dtype='float64')
            self._test_op(expected, tfa_utils.log_to_linear, spectra)

        # explicit reference power
        reference_power = 10
        for spectra, expected in cases:
            spectra = np.array(spectra, dtype='float64')
            expected = np.array(expected, dtype='float64')
            expected *= reference_power
            self._test_op(
                expected, tfa_utils.log_to_linear, spectra, reference_power)
