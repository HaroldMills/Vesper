"""Module containing class `FeatureComputer`."""


import numpy as np

from vesper.util.settings import Settings
import vesper.util.data_windows as data_windows
import vesper.util.signal_utils as signal_utils
import vesper.util.time_frequency_analysis_utils as tfa_utils


class FeatureComputer:

    """Computes classification features from clip waveforms."""


    def __init__(self, settings):

        self._settings = settings

        s = settings
        sample_rate = s.waveform_sample_rate

        # Get waveform trimming start and end indices.
        self._start_time_index = signal_utils.seconds_to_frames(
            s.waveform_start_time, sample_rate)
        waveform_length = signal_utils.seconds_to_frames(
            s.waveform_duration, sample_rate)
        self._end_time_index = self._start_time_index + waveform_length

        # Get spectrogram settings.
        window_size = signal_utils.seconds_to_frames(
            s.spectrogram_window_size, sample_rate)
        hop_size = signal_utils.seconds_to_frames(
            s.spectrogram_hop_size, sample_rate)
        dft_size = tfa_utils.get_dft_size(window_size)
        self._spectrogram_settings = Settings(
            window=data_windows.create_window('Hann', window_size),
            hop_size=hop_size,
            dft_size=dft_size,
            reference_power=1)

        # Get spectrogram shape.
        num_spectra = tfa_utils.get_num_analysis_records(
            waveform_length, window_size, hop_size)
        num_bins = dft_size // 2 + 1
        self._spectrogram_shape = (num_spectra, num_bins)
        self._augmented_spectrogram_shape = (1,) + self._spectrogram_shape

        # Get spectrogram trimming start and end indices.
        self._start_freq_index = _freq_to_dft_bin_num(
            settings.spectrogram_start_freq, sample_rate, dft_size)
        self._end_freq_index = _freq_to_dft_bin_num(
            settings.spectrogram_end_freq, sample_rate, dft_size) + 1


    @property
    def min_waveform_length(self):
        return self._end_time_index


    def compute_features(self, waveforms):

        waveforms = self.trim_waveforms(waveforms)

        spectrograms = self.compute_spectrograms(waveforms)

        spectrograms = self.trim_spectrograms(spectrograms)

        if self._settings.spectrogram_min_power is not None:
            self.clip_spectrogram_powers(spectrograms)

        if self._settings.spectrogram_mean is not None:
            self.normalize_spectrograms(spectrograms)

        return self.flatten_spectrograms(spectrograms)


    def trim_waveforms(self, waveforms):
        return waveforms[:, self._start_time_index:self._end_time_index]


    def compute_spectrograms(
            self, waveforms, notification_period=None, listener=None):

        num_waveforms = len(waveforms)

        if num_waveforms == 1:

            spectrogram = self._compute_spectrogram(waveforms[0])
            return spectrogram.reshape(self._augmented_spectrogram_shape)

        else:
            # have more than one waveform or zero waveforms

            spectrograms_shape = (num_waveforms,) + self._spectrogram_shape
            spectrograms = np.zeros(spectrograms_shape, dtype='float32')

            for i in range(num_waveforms):

                if notification_period is not None and \
                        i % notification_period == 0 and \
                        i != 0:
                    listener(i)

                waveform = waveforms[i, :]
                spectrogram = self._compute_spectrogram(waveform)
                spectrograms[i, :, :] = spectrogram

            return spectrograms


    def _compute_spectrogram(self, waveform):
        s = self._spectrogram_settings
        spectrogram = tfa_utils.compute_spectrogram(
            waveform, s.window.samples, s.hop_size, s.dft_size)
        return tfa_utils.linear_to_log(spectrogram, s.reference_power)


    def trim_spectrograms(self, spectrograms):
        return spectrograms[:, :, self._start_freq_index:self._end_freq_index]


    def configure_spectrogram_power_clipping(self, spectrograms):

        """
        Finds spectrogram power clipping limits on the tails of the
        specified spectrograms' combined histogram.

        This function finds clipping limits for spectrogram bin values
        that lie on the lower and upper tails of the spectrograms' combined
        histogram. The clipping limits are chosen to eliminate from the
        histogram the largest number of histogram bins from each tail
        whose counts sum to half of the fraction
        `self._settings.spectrogram_power_clipping_fraction` of the
        histogram's total sum.
        """


        settings = self._settings

        if settings.spectrogram_power_clipping_fraction != 0:

            histogram, edges = np.histogram(spectrograms, bins=1000)
            f = settings.spectrogram_power_clipping_fraction / 2
            t = f * np.sum(histogram)

            s = 0
            i = 0
            while s + histogram[i] <= t:
                i += 1

            s = 0
            j = len(histogram)
            while s + histogram[j - 1] <= t:
                j -= 1

            min_power = edges[i]
            max_power = edges[j]

            # Plot histogram with power limits.
#             import matplotlib.pyplot as plt
#             limits = (edges[0], edges[-1])
#             plt.figure(1)
#             plt.plot(edges[:-1], histogram)
#             plt.axvline(min_power, color='r')
#             plt.axvline(max_power, color='r')
#             plt.xlim(limits)
#             plt.show()

        else:

            min_power = None
            max_power = None

        settings.spectrogram_min_power = min_power
        settings.spectrogram_max_power = max_power


    def clip_spectrogram_powers(self, spectrograms):

        # Clip powers below minimum to minimum.
        min_power = self._settings.spectrogram_min_power
        spectrograms[spectrograms < min_power] = min_power

        # Clip powers above maximum to maximum.
        max_power = self._settings.spectrogram_max_power
        spectrograms[spectrograms > max_power] = max_power


    def configure_spectrogram_normalization(self, spectrograms):

        settings = self._settings

        if settings.spectrogram_normalization_enabled:
            mean = spectrograms.mean()
            std = spectrograms.std()

        else:
            mean = None
            std = None

        settings.spectrogram_mean = mean
        settings.spectrogram_standard_dev = std


    def normalize_spectrograms(self, spectrograms):
        settings = self._settings
        spectrograms -= settings.spectrogram_mean
        spectrograms /= settings.spectrogram_standard_dev


    def flatten_spectrograms(self, spectrograms):
        return spectrograms.reshape((len(spectrograms), -1))


# TODO: Move this to time-frequency analysis utils.
def _freq_to_dft_bin_num(freq, sample_rate, dft_size):
    bin_size = sample_rate / dft_size
    return int(round(freq / bin_size)) % dft_size
