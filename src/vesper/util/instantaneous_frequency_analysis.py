"""Module containing `InstantaneousFrequencyAnalysis` class."""


import numpy as np

from vesper.util.time_frequency_analysis import TimeFrequencyAnalysis
import vesper.util.time_frequency_analysis_utils as tfa_utils


class InstantaneousFrequencyAnalysis(TimeFrequencyAnalysis):
    
    
    def __init__(self, sound, params):
        
        self.dft_size, freqs = tfa_utils.get_dft_analysis_data(
            sound.sample_rate, params.dft_size, params.window.size)
        
        super(InstantaneousFrequencyAnalysis, self).__init__(
            sound, params.window, params.hop_size, freqs)
        
        
    def _analyze(self):
        
        samples = self.sound.samples
        window = self.window
        
        numerator = tfa_utils.compute_stft(
            samples, window.derivative, self.hop_size, self.dft_size)
        
        denominator = tfa_utils.compute_stft(
            samples, window.samples, self.hop_size, self.dft_size)
        
        # TODO: What if the denominator is zero? For example, what should
        # we yield for silence?
        f = self.sound.sample_rate / (2 * np.pi)
        deltas = f * -np.imag(numerator / denominator)
        
        return deltas
                     

    @property
    def freq_spacing(self):
        return self.sound.sample_rate / (self.dft_size + 1)
