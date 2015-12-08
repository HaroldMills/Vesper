"""Trains an NFC species classifier."""


from __future__ import print_function
import os.path
import random
import sys

import numpy as np
import pandas as pd

from vesper.archive.archive import Archive
from vesper.util.bunch import Bunch
import vesper.util.data_windows as data_windows
import vesper.util.nfc_classification_utils as nfc_classification_utils
import vesper.util.signal_utils as signal_utils


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_ARCHIVE_NAME = 'MPG Ranch 2012-2014'
_PICKLE_FILE_NAME = 'Call Clips.pkl'


_CONFIGS = {
            
    'Tseep': Bunch(
        detector_name = 'Tseep',
        segment_duration = .1,
        spectrogram_params=Bunch(
            window=data_windows.create_window('Hann', 110),
            hop_size=55,
            dft_size=128,
            ref_power=1),
        min_freq=4000,
        max_freq=10000,
        min_power=-10,
        max_power=65,
        pooling_block_size=(2, 2),
        include_norm_in_features=False,
        ),
            
    'Thrush': Bunch(
        detector_name = 'Thrush'
        )
            
}


def _main():
    
    # Seed random number generators so that script yields identical
    # results on repeated runs.
    random.seed(0)
    np.random.seed(0)
    
    config = _CONFIGS[sys.argv[1]]
    
    print('Getting call clips from archive...')
    clips = _get_clips_from_archive(config)
    print('Got {} clips.\n'.format(len(clips)))
    
    print('Extracting segments...')
    clips = _extract_clip_segments(clips, config)
    print('Extracted {} segments.\n'.format(len(clips)))
    
    print('Computing features...')
    clips = _compute_segment_features(clips, config)

    print('Pickling DataFrame...')    
    _save_clips(clips)
    
    print('Done.')
    
    
def _get_clips_from_archive(config):
    
    clips = _get_clips_list_from_archive(config.detector_name)
    clips = _create_clips_dataframe(clips, config)
    
    station_names = ['Floodplain', 'Sheep Camp', 'Ridge']
    clips = clips[clips['station'].isin(station_names)]
    clips = clips[clips['detector'] == 'Tseep']
    clips = clips[clips['clip_class'] != 'Noise']
    clips = clips[clips['selection'].notnull()]
    
    return clips
    
    
def _get_clips_list_from_archive(detector_name):
    archive_dir_path = os.path.join(_DIR_PATH, _ARCHIVE_NAME)
    archive = Archive(archive_dir_path)
    archive.open()
    clips = archive.get_clips(
        detector_name=detector_name, clip_class_name='Call*')
    archive.close()
    return clips


def _create_clips_dataframe(clips, config):
    
    data = {
        'station': [c.station.name for c in clips],
        'detector': [c.detector_name for c in clips],
        'night': [c.night for c in clips],
        'start_time': [c.start_time for c in clips],
        'clip_class': [c.clip_class_name for c in clips],
        'samples': [c.sound.samples for c in clips],
        'sample_rate': [c.sound.sample_rate for c in clips],
        'selection': [c.selection for c in clips]
    }
    
    columns = [
        'station', 'detector', 'night', 'start_time', 'clip_class',
        'samples', 'sample_rate', 'selection']
    
    return pd.DataFrame(data, columns=columns)
        
        
def _extract_clip_segments(clips, config):
    
    # I suspect there is a more efficient way to do this with Pandas,
    # but I haven't found it yet (see the commented-out code below).
    clips['segment'] = [
        _extract_clip_segment(clip, config.segment_duration)
        for _, clip in clips.iterrows()]
        
    # Not sure why this doesn't work. The idea is to assign a `Series`
    # of NumPy arrays to the `'segment'` column. Unfortunately, though,
    # returning a NumPy array from `_extract_clip_segment` seems to mess
    # up the number of columns somewhere somehow. 
#     clips['segment'] = clips.apply(
#         _extract_clip_segment, axis=1, duration=config.segment_duration)
    
    return clips
    
    
def _extract_clip_segment(clip, duration):
    
    if clip['selection'] is None:
        return None
    
    else:
        
        selection_start_index, selection_length = clip['selection']
        selection_center_index = selection_start_index + selection_length // 2
        length = signal_utils.seconds_to_frames(duration, clip['sample_rate'])
        start_index = selection_center_index - length // 2
        
        if start_index < 0:
            return None
        
        else:
            end_index = start_index + length
            return clip['samples'][start_index:end_index]


def _compute_segment_features(clips, config):
    
    pairs = [
        _compute_segment_features_aux(clip, config)
        for _, clip in clips.iterrows()]
    
    spectra, features = zip(*pairs)
    
    clips['spectra'] = list(spectra)
    clips['features'] = list(features)
    
    return clips

    
def _compute_segment_features_aux(clip, config):
    segment = Bunch(samples=clip['segment'], sample_rate=clip['sample_rate'])
    features, spectra, _ = \
        nfc_classification_utils.get_segment_features(segment, config)
    return (spectra, features)


def _save_clips(clips):
    file_path = os.path.join(_DIR_PATH, _PICKLE_FILE_NAME)
    clips.to_pickle(file_path)
    
    
if __name__ == '__main__':
    _main()
