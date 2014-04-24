from __future__ import print_function

import unittest

import numpy as np

from nfc.util.bunch import Bunch
from nfc.util.spectrogram import Spectrogram


class SpectrogramUtilsTests(unittest.TestCase):
    
    
    def test_spectrogram(self):
        
        cases = [
            (-1, [0, 4, 0, 0, 0]),
            (0, [8, 0, 0, 0, 0]),
            (1, [0, 4, 0, 0, 0]),
            (2, [0, 0, 4, 0, 0]),
            (3, [0, 0, 0, 4, 0]),
            (4, [0, 0, 0, 0, 8])
        ]
        
        for f, expected_spectrum in cases:
        
            n = 2 * (len(expected_spectrum) - 1)
            
            samples = np.cos(2 * np.pi * f * np.arange(2 * n) / float(n))
            sound = Bunch(samples=samples, sample_rate=1.)
            
            hop_size = n / 2
            
            params = Bunch(
                window=np.ones(n),
                hop_size=hop_size,
                dft_size=None,
                ref_power=None)
            
            gram = Spectrogram(sound, params)
            
            self.assertEqual(gram.frame_rate, 1. / hop_size)
            
            expected_spectrum = np.array(expected_spectrum, dtype='float')
            
            for spectrum in gram.spectra:
                
                m = len(spectrum)
                
                self.assertEqual(m, len(expected_spectrum))
                
                for i in xrange(m):
                    self.assertAlmostEqual(
                        spectrum[i], expected_spectrum[i], places=6)
