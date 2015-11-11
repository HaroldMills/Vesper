from __future__ import print_function
import os.path

import pandas as pd


_CSV_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CALLS_FILE_PATH = os.path.join(_CSV_DIR_PATH, 'Call Clips.csv')
_NOISES_FILE_PATH = os.path.join(_CSV_DIR_PATH, 'Tseep Noise Clips.csv')
_STATION_NAMES = ['Floodplain NFC', 'Sheep Camp NFC', 'Ridge NFC']


def _main():
    
    all_clips = _read_csv_files()
    
    # Exclude rows not from stations of interest.
    mask = all_clips['Station'].isin(_STATION_NAMES)
    all_clips = all_clips[mask]
    
    # Add coarse clip class column.
    all_clips['Coarse Clip Class'] = \
        all_clips['Clip Class'].apply(_get_first_clip_class_component)
        
    for detector_name in ['Tseep', 'Thrush']:
        
        mask = all_clips['Detector'] == detector_name
        clips = all_clips[mask]
        
        data = {}
        
        # Get per-station counts.
        for station_name in _STATION_NAMES:
            mask = clips['Station'] == station_name
            counts = clips[mask]['Coarse Clip Class'].value_counts()
            data[station_name] = counts
            
        # Get total counts.
        total_counts = clips['Coarse Clip Class'].value_counts()
        data['Total'] = total_counts
        
        counts = pd.DataFrame(data).fillna(0)
        
        print(detector_name + ':')
        print(counts)
        print()
        

def _read_csv_files():
    calls = pd.read_csv(_CALLS_FILE_PATH)
    noises = pd.read_csv(_NOISES_FILE_PATH)
    return calls.append(noises)


def _get_first_clip_class_component(clip_class):
    
    if clip_class.startswith('Call'):
        return 'Call'
    
    else:
        return clip_class


if __name__ == '__main__':
    _main()
