import numpy as np

from vesper.tests.test_case import TestCase
from vesper.util.bunch import Bunch
from vesper.util.data_windows import RectangularWindow
from vesper.util.spectrogram import Spectrogram
import vesper.util.time_frequency_analysis_utils as tfa_utils


_SAMPLE_RATE = 1000


class SpectrogramTests(TestCase):


    def test_spectrogram(self):

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

                        self._test_spectrogram(
                            num_channels, dft_size, hop_size, bin_num)


    def _test_spectrogram(self, num_channels, dft_size, hop_size, bin_num):

        num_samples = dft_size * 2
        samples = self._create_test_signal(
            num_channels, num_samples, dft_size, bin_num)
        audio = Bunch(samples=samples, sample_rate=_SAMPLE_RATE)

        window = RectangularWindow(dft_size)
        settings = Bunch(
            window=window,
            hop_size=hop_size,
            dft_size=dft_size,
            reference_power=None)

        spectrogram = Spectrogram(audio, settings)
        spectra = spectrogram.spectra

        expected = self._get_expected_spectra(
            num_channels, num_samples, hop_size, dft_size, bin_num)

        self.assertTrue(np.allclose(spectra, expected))
        self.assertEqual(spectrogram.freq_spacing, _SAMPLE_RATE / dft_size)


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
        spectrum[bin_num] = dft_size
        if bin_num != 0 and bin_num != num_bins - 1:
            spectrum[bin_num] /= 2
        return spectrum.reshape((1, len(spectrum)))
