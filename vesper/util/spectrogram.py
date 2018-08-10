"""Module containing `Spectrogram` class."""


from vesper.util.time_frequency_analysis import TimeFrequencyAnalysis
import vesper.util.time_frequency_analysis_utils as tfa_utils


class Spectrogram(TimeFrequencyAnalysis):


    def __init__(self, audio, settings):

        """
        Initializes this spectrogram.

        :Parameters:

            audio : `object`
                the audio of which to compute the spectrogram.

                This parameter must be a Python object with the
                following attributes:

                    samples : NumPy array
                        audio samples

                    sample_rate : `float`
                        the sample rate of the audio in hertz.

            settings : `object`
                the spectrogram settings.

                This parameter must be a Python object with the
                following attributes:

                    window : `object`
                        the data window to use for the spectrogram.

                        The data window may be of any length. It must
                        have a `samples` attribute that is a NumPy
                        array of window samples.

                    hop_size : `int`
                        the spectrogram hop size in samples.

                    dft_size : `int`
                        the DFT size for the spectrogram, in samples,
                        or `None`.

                        The DFT size must be either a power of two
                        or `None`. If `None`, the implied DFT size is
                        the smallest power of two that is at least the
                        window size.

                    reference_power : `float`
                        the reference power for the spectrogram, or `None`.

                        If the reference power is not `None`, the
                        units of the returned spectrogram magnitude
                        are decibels with respect to the reference
                        power. If the reference power is `None`, no
                        logarithms are taken.
        """


        self.dft_size, freqs = tfa_utils.get_dft_analysis_data(
            audio.sample_rate, settings.window.size, settings.dft_size)

        self.reference_power = settings.reference_power

        super(Spectrogram, self).__init__(
            audio, settings.window, settings.hop_size, freqs)


    def _analyze(self):

        spectra = tfa_utils.compute_spectrogram(
            self.audio.samples, self.window.samples, self.hop_size,
            self.dft_size)

        tfa_utils.scale_spectrogram(spectra, out=spectra)

        if self.reference_power is not None:
            tfa_utils.linear_to_log(spectra, self.reference_power, out=spectra)

        return spectra


    @property
    def spectra(self):
        return self.analyses


    @property
    def freq_spacing(self):
        return self.audio.sample_rate / self.dft_size
