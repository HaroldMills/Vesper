"""
Exports clip classification data from Vesper 0.1 archives.

This script exports tseep or thrush classification data from a pair of
Vesper 0.1 archives to an HDF5 file. The script gets call clips from
one archive and noise clips from another.
"""


import argparse
import os.path

import h5py

from vesper.archive.archive import Archive


_DIR_PATH = r'C:\Users\Harold\Desktop\NFC\Data\MPG Ranch'
_CALL_ARCHIVE_NAME = 'MPG Ranch 2012-2014'
_NOISE_ARCHIVE_NAME_FORMAT = 'MPG Ranch Sampled 2014 {}'
_HDF5_FILE_NAME_FORMAT = 'Vesper {} Classification Data 0.1.hdf5'


def _main():
    
    detector_name = _parse_args()
    
    print('Getting stations from call archive...')
    stations = _get_stations_from_archive(_CALL_ARCHIVE_NAME)
    print(
        'Got {} stations ({}).\n'.format(
            len(stations), sorted(s.name for s in stations)))

    print('Getting clips from archives...')
    clips = _get_clips_from_archives(detector_name)
    print('Got {} clips.\n'.format(len(clips)))
    
    print('Writing HDF5 file...')
    _write_hdf5_file(detector_name, stations, clips)
    

def _parse_args():
    description = (
        'Export classification data for Tseep or Thrush clips to an '
        'HDF5 file.')
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('detector_name', choices=('Tseep', 'Thrush'))
    args = parser.parse_args()
    return args.detector_name


def _get_stations_from_archive(archive_name):
    archive_dir_path = _create_full_path(archive_name)
    archive = Archive(archive_dir_path)
    archive.open()
    stations = archive.stations
    archive.close()
    return stations


def _get_clips_from_archives(detector_name):
    call_clips = _get_clips_from_archive(
        _CALL_ARCHIVE_NAME, detector_name, 'Call*')
    noise_archive_name = _NOISE_ARCHIVE_NAME_FORMAT.format(detector_name)
    noise_clips = _get_clips_from_archive(
        noise_archive_name, detector_name, 'Noise')
    return call_clips + noise_clips
    

def _get_clips_from_archive(archive_name, detector_name, clip_class_name):
    archive_dir_path = _create_full_path(archive_name)
    archive = Archive(archive_dir_path)
    archive.open()
    clips = archive.get_clips(
        detector_name=detector_name, clip_class_name=clip_class_name)
    archive.close()
    return clips


def _create_full_path(*parts):
    return os.path.join(_DIR_PATH, *parts)


def _write_hdf5_file(detector_name, stations, clips):
    
    file_name = _HDF5_FILE_NAME_FORMAT.format(detector_name)
    path = _create_full_path(file_name)
    
    with h5py.File(path, 'w') as f:
        
        clips_group = f.create_group('Clips')
        
        clipCount = 0
        noiseCount = 0
        callCount = 0
    
        # Keep track of station names referred to by clips.
        station_names = set()
        
        for clip in clips:
            
            clip_class_name = clip.clip_class_name
        
            if clip_class_name == 'Noise' or \
                    clip_class_name.startswith('Call') and \
                    clip.selection is not None:
            
                station_name = clip.station.name
                if station_name.endswith(' NFC'):
                    station_name = station_name[:-len(' NFC')]

                station_names.add(station_name)
                
                mic_name = 'SMX-NFC'
                start_time = _format_datetime(clip.start_time)
                name = '{} {} {}'.format(station_name, mic_name, start_time)

                sound = clip.sound
                
                dset = clips_group.create_dataset(
                    name, data=sound.samples, dtype='int16')
                dset.attrs['station_name'] = station_name
                dset.attrs['microphone_name'] = mic_name
                dset.attrs['start_utc_timestamp'] = clip.start_time.timestamp()
                dset.attrs['length'] = len(sound.samples)
                dset.attrs['sample_rate'] = sound.sample_rate
                dset.attrs['classification'] = clip.clip_class_name
                
                if clip_class_name.startswith('Call'):
                    callCount += 1
                    (start_index, length) = clip.selection
                    dset.attrs['nfc_start_index'] = start_index
                    dset.attrs['nfc_length'] = length
                    
                else:
                    noiseCount += 1
                
                clipCount += 1
                
                if clipCount % 1000 == 0:
                    print('{} clips...'.format(clipCount))
                
        print('stations...')
        
        stations_group = f.create_group('Stations')
        
        retained_station_names = set()
        
        for station in stations:
            
            if station.name in station_names:
                # station is referred to by one or more clips
                
                retained_station_names.add(station.name)
                
                group = stations_group.create_group(station.name)
                group.attrs['name'] = station.name
                group.attrs['latitude'] = station.latitude
                group.attrs['longitude'] = station.longitude
                group.attrs['elevation'] = station.elevation
                group.attrs['time_zone_name'] = str(station.time_zone)
                
        print((
            '\nWrote {} of {} clips to HDF5 file. {} were calls and {} '
            'were noises.').format(
                clipCount, len(clips), callCount, noiseCount))
            
        print((
            'Wrote {} of {} stations ({}) to HDF5 file. There were no clips '
            'for the other stations.').format(
                len(retained_station_names),
                len(stations),
                sorted(retained_station_names)))
            
    
def _format_datetime(dt):
    us = '.{:06}'.format(dt.microsecond).rstrip('.0')
    return dt.strftime('%Y-%m-%dT%H:%M:%S') + us + 'Z'


if __name__ == '__main__':
    _main()
    