"""
Analyze call and noise clip CSV files and print tables of Tseep and Thrush
call, noise, and unclassifier clip counts.
"""


from __future__ import print_function
import os.path

import pandas as pd


_CSV_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CALLS_FILE_NAME = 'Call Clips.csv'
_NOISES_FILE_NAME_SUFFIX = ' Noise Clips.csv'
_STATION_NAMES = ['Floodplain NFC', 'Sheep Camp NFC', 'Ridge NFC']
_DETECTOR_NAMES = ['Tseep', 'Thrush']


def _main():
    
    all_clips = _read_csv_files()
    
    # Add coarse clip class column.
    all_clips['Coarse Clip Class'] = \
        all_clips['Clip Class'].apply(_get_first_clip_class_component)
        
    for detector_name in _DETECTOR_NAMES:
        
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
    df = _read_clips_csv_file()
    for detector_name in _DETECTOR_NAMES:
        df = df.append(_read_noises_csv_file(detector_name))
    return df


def _read_clips_csv_file():
    
    df = _read_csv_file(_CALLS_FILE_NAME)
    
    # Exclude noise clips.
    mask = df['Clip Class'] != 'Noise'
    df = df[mask]
    
    return df


def _read_csv_file(file_name):
    
    file_path = os.path.join(_CSV_DIR_PATH, file_name)
    df = pd.read_csv(file_path)
    
    # Exclude rows not for stations of interest
    mask = df['Station'].isin(_STATION_NAMES)
    df = df[mask]
    
    return df


def _read_noises_csv_file(detector_name):
    return _read_csv_file(detector_name + _NOISES_FILE_NAME_SUFFIX)
    
    
def _get_first_clip_class_component(clip_class):
    
    if clip_class.startswith('Call'):
        return 'Call'
    
    else:
        return clip_class


if __name__ == '__main__':
    _main()
