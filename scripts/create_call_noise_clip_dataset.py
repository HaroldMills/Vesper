"""
Creates a call/noise classification dataset.

The dataset contains call and noise clips selected at random from an
NFC archive.

nfc_dataset
    create_call_and_noise_dataset(
        archive_dir_path, dataset_dir_path, num_clips, calls_fraction)
    load_dataset(dir_path)
    
Dataset persists in a directory containing sound files and a .csv file
with lines like:

Alfred_Tseep_2012-09-01_21.00.50.000.wav,0
Alfred_Tseep_2012-09-01_21.01.26.000.wav,1

For sklearn, want Bunch with the following attributes:
    data - m x n array of feature values, where m is the number of
           clips and n is the number of features.
    target - length m 1-d binary array of classifications (0 = noise, 1 = call)
    target_names - ['noise', 'call']
    
The load_dataset function creates such a Bunch
"""

'''
call/noise classification

denoise
    assume that first and last n ms are noise
    measure noise spectrum
    subtract noise spectrum
    
    cluster spectra (after PCA? how many clusters?)
    
extract features
    equivalent bandwidth (maybe smallest average in 50 ms window?)
    spectral entropy (maybe smallest average in 50 ms window?)
    duration
    
classify

Useful NFC Viewer features:

    Select some clips and then perform some kind of analysis on them,
    possibly involving UI. For example, might cluster spectra and then
    indicate clustering on top of spectrogram. Or might plot equivalent
    bandwidth on top of spectrogram. Or might display something in a
    new window.
    
    Side-by-side comparisons of spectrograms before and after denoising
    (maybe in popup window, or maybe in side-by-side clips panels).
'''


from __future__ import print_function

from nfc.util.preferences import preferences as prefs
import nfc.classification.clip_dataset as clip_dataset


_TEST_DATASET_DIR_PATH = '/Users/Harold/Desktop/NFC/Datasets/Test'


def main():
    clip_dataset.create_clip_dataset(
        prefs['archiveDirPath'], _TEST_DATASET_DIR_PATH, 100,
        ('Call', 'Noise'))
        
        
if __name__ == '__main__':
    main()
