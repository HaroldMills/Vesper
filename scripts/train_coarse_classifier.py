import time

import h5py
import numpy as np

from vesper.util.bunch import Bunch
from vesper.util.spectrogram import Spectrogram
import vesper.util.data_windows as data_windows
import vesper.util.time_frequency_analysis_utils as tfa_utils


_FILE_PATH = r'C:\Users\Harold\Desktop\clips.hdf5'


_SETTINGS = {
     
    'Tseep': Bunch(
        detector_name = 'Tseep',
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        dev_set_size = 5000,
        test_set_size = 5000
    )
             
#     'Tseep': Bunch(
#         detector_name = 'Tseep',
#         spectrogram_params=Bunch(
#             window=data_windows.create_window('Hann', 256),
#             hop_size=128,
#             dft_size=256,
#             ref_power=1),
#         dev_set_size = 5000,
#         test_set_size = 5000
#     )
             
}


# TODO: Get from HDF5 file? Or make independent and resample clips as needed?
_SAMPLE_RATE = 22050


def _main():
    
    settings = _SETTINGS['Tseep']
    
    print('Reading dataset...')
    samples, classifications = _read_dataset()
    
    num_clips = samples.shape[0]
    num_calls = int(np.sum(classifications))
    num_noises = num_clips - num_calls
    
    print(
        'Read {} clips, {} calls and {} noises.'.format(
            num_clips, num_calls, num_noises))
    
    print('Computing spectrograms...')
    start_time = time.time()
    spectrograms = _compute_spectrograms(samples, settings)
    elapsed_time = time.time() - start_time
    spectrogram_rate = num_clips / elapsed_time
    spectrum_rate = spectrogram_rate * spectrograms[0].shape[0]
    print((
        'Computed {} spectrograms of shape {} in {:.1f} seconds, an average '
        'of {:.1f} spectrograms and {:.1f} spectra per second.').format(
            num_clips, spectrograms[0].shape, elapsed_time, spectrogram_rate,
            spectrum_rate))
        

def _read_dataset():
    
    with h5py.File(_FILE_PATH) as f:
        samples = f['samples'][...]
        classifications = f['classifications'][...]
        
    return samples, classifications
    
        
def _compute_spectrograms(samples, settings):
    
    params = settings.spectrogram_params
    
    num_clips = samples.shape[0]
    num_spectra, num_bins = _get_spectrogram_shape(samples, params)

    spectrograms = np.zeros(
        (num_clips, num_spectra, num_bins), dtype='float32')
    
    for i in range(num_clips):
        if i != 0 and i % 10000 == 0:
            print('    {}...'.format(i))
        clip_samples = samples[i, :]
        spectrogram = _compute_spectrogram(clip_samples, params)
        spectrograms[i, :, :] = spectrogram
        
    return spectrograms
    
    
def _get_spectrogram_shape(samples, params):
    spectrogram = _compute_spectrogram(samples[0], params)
    return spectrogram.shape


def _compute_spectrogram_old(samples, params):
    sound = Bunch(samples=samples, sample_rate=_SAMPLE_RATE)
    spectrogram = Spectrogram(sound, params)
    return spectrogram.spectra
    
    
def _compute_spectrogram(samples, params):
    return tfa_utils.compute_spectrogram(
        samples,
        params.window.samples,
        params.hop_size,
        params.dft_size)

    
if __name__ == '__main__':
    _main()
    