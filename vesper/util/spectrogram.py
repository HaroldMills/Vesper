"""Module containing `Spectrogram` class."""


from vesper.util.time_frequency_analysis import TimeFrequencyAnalysis
import vesper.util.time_frequency_analysis_utils as tfa_utils


# TODO: Compare this spectrogram carefully to that computed by the
# Matplotlib `specgram` function, in terms of both functionality
# and efficiency.


class Spectrogram(TimeFrequencyAnalysis):
     
     
    def __init__(self, sound, params):
         
        """
        Initializes this spectrogram.
         
        :Parameters:
         
            sound : `object`
                the sound of which to compute the spectrogram.
                 
                This parameter must be a Python object with the
                following attributes:
                 
                    samples : NumPy array
                        the samples of the sound
                         
                    sample_rate : `float`
                        the sample rate of the sound in hertz.
             
            params : `object`
                the spectrogram parameters.
             
                This parameter must be a Python object with the
                following attributes:
             
                    window : NumPy array
                        the data window to use for the spectrogram.
                 
                        The data window may be of any length.
                 
                    hop_size : `int`
                        the spectrogram hop size in samples.
                         
                    dft_size : `int`
                        the DFT size for the spectrogram, in samples,
                        or `None`.
                         
                        The DFT size must be either a power of two
                        or `None`. If `None`, the DFT size is taken to
                        be the smallest power of two that is at least
                        the window size.
                         
                    ref_power : `float`
                        the reference power for the spectrogram, or `None`.
                         
                        If the reference power is not `None`, the
                        units of the returned spectrogram magnitude
                        are decibels with respect to the reference
                        power. If the reference power is `None`, no
                        logarithms are taken.
        """
     
     
        self.dft_size, freqs = tfa_utils.get_dft_analysis_data(
            sound.sample_rate, params.dft_size, params.window.size)
        
        self.ref_power = params.ref_power
             
        super(Spectrogram, self).__init__(
            sound, params.window, params.hop_size, freqs)
         
         
    def _analyze(self):
        
        spectra = tfa_utils.compute_spectrogram(
            self.sound.samples, self.window.samples, self.hop_size,
            self.dft_size)
        
        tfa_utils.adjust_spectrogram_powers(spectra, self.dft_size)
        
        if self.ref_power is not None:
            tfa_utils.linear_to_log(spectra, self.ref_power, spectra)
            
        return spectra
                     

    @property
    def spectra(self):
        return self.analyses
    
    
    @property
    def freq_spacing(self):
        return self.sound.sample_rate / (self.dft_size + 1)
