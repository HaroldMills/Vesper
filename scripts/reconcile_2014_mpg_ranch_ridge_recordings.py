"""
Reconciles recordings indicated in the MPG Ranch 2014 archive database for
the Ridge station with the set of recording audio files I have.

For many nights, there are several short recordings indicated in the
database, but I have only one disk file, where the disk file was
apparently obtained by concatenating shorter files corresponding to the
recordings in the database.

The Ridge recordings were originally made at 192 kHz, with several
files per night. Those files were downsampled independently to 22050 Hz,
and then the Old Bird detectors were run on the individual 22050 Hz
files.

This script figures out which portion of which disk file corresponds
to each recording in the database, and when needed extracts that portion
to create an appropriate smaller file. The script puts each new file in
the same directory as the file from which it is extracted.
"""


from collections import defaultdict
from pathlib import Path

import pytz

# Set up Django. This must happen before any use of Django, including
# ORM class imports.
import vesper.util.django_utils as django_utils
django_utils.set_up_django()

from vesper.django.app.models import Recording, Station
from vesper.mpg_ranch.recording_file_parser import RecordingFileParser
from vesper.signal.wave_audio_file import WaveAudioFileReader
import vesper.util.audio_file_utils as audio_file_utils


RECORDING_DIR_PATHS = [
    Path('/Volumes/MPG Ranch 2012-2015/spring_2014'),
    Path('/Volumes/MPG Ranch 2012-2015/fall_2014')
]

SHOW_MATCHES = False
SHOW_NON_MATCHES = False
SPLIT_FILES = True

SAMPLE_RATE = 22050

TWO_SECONDS = 2 * SAMPLE_RATE
"""
The number of sample frames in two seconds of a recording.

The `populate_archive` script that created the recordings in the archive
database added two seconds' worth of samples to each recording as a
workaround to the problem that some clips extended past the ends of
their recordings. This problem probably stemmed from a combination of
the inaccuracy of the clip start times recorded by the Old Bird
detectors, and the fact that the detectors sometimes append zeros
to clips extracted from the ends of recordings.
"""

TIME_ZONE = pytz.timezone('US/Mountain')


def main():
    
    recording_lists = get_recordings()
    file_lists = get_files()
    
    nights = sorted(recording_lists.keys())
    
    for night in nights:
        
        recordings = recording_lists[night]
        files = file_lists[night]
        
        groups = group_recordings_and_files_by_start_times(recordings, files)
        
        show_groups(night, groups)
        
        if SPLIT_FILES:
            split_files(groups)


def get_recordings():
    
    recording_lists = defaultdict(list)

    recordings = Recording.objects.filter(station__name='Ridge')
    
    for r in recordings:
        night = r.station.get_night(r.start_time)
        recording_lists[night].append(r)
    
    for recording_list in recording_lists.values():
        recording_list.sort(key=lambda r: r.start_time)
        
    return recording_lists


def get_files():
    
    file_lists = defaultdict(list)
    
    station = Station.objects.get(name='Ridge')
    file_parser = RecordingFileParser({station})
    
    for dir_path in RECORDING_DIR_PATHS:
        
        for file_path in dir_path.glob('**/*.wav'):
            
            if str(file_path.name).lower().startswith('ridge'):
                
                try:
                    file = file_parser.parse_file(str(file_path))
                    
                except Exception:
                    
                    print(
                        f'Warning: Could not parse recording file '
                        f'"{file_path}. File will be ignored.')
                    
                    continue
                
                else:
                    
                    night = station.get_night(file.start_time)
                    file_lists[night].append(file)
                    
    for file_list in file_lists.values():
        file_list.sort(key=lambda f: f.start_time)
    
    return file_lists


def group_recordings_and_files_by_start_times(recordings, files):
    
    index_pairs = find_matching_start_times(recordings, files)
    
    if len(index_pairs) == 0 or index_pairs[0] != (0, 0):
        index_pairs = [(0, 0)] + index_pairs
    
    index_pairs.append([len(recordings), len(files)])
        
    group_count = len(index_pairs) - 1
    groups = []
    
    for i in range(group_count):
        
        start_r, start_f = index_pairs[i]
        end_r, end_f = index_pairs[i + 1]
               
        group_recordings = recordings[start_r:end_r]
        group_files = files[start_f:end_f]
        
        groups.append((group_recordings, group_files))
    
    return groups


def find_matching_start_times(recordings, files):
    
    index_pairs = []
    
    i = 0
    j = 0
    
    while i != len(recordings) and j != len(files):
        
        if recordings[i].start_time == files[j].start_time:
            index_pairs.append((i, j))
            i += 1
            j += 1
            
        elif recordings[i].start_time < files[j].start_time:
            i += 1
            
        else:
            j += 1
    
    return index_pairs


def show_groups(night, groups):
    
    for recordings, files in groups:
        
        total_recording_length = sum(r.length for r in recordings)
        total_file_length = sum(f.length for f in files)
        
        # Get difference between total recording and file lengths,
        # accounting for two seconds of padding that was added to
        # each recording by the `populate_archive` script.
        diff = (total_recording_length - total_file_length) / 22050
        diff -= 2 * len(recordings)
        
        if SHOW_MATCHES and diff == 0 or SHOW_NON_MATCHES and diff != 0:
            
            print(f'{night}:')
            
            print(f'    Recordings:')
            for recording in recordings:
                print(f'        {str(recording)} {recording.length}')
            print(f'        Total recording length: {total_recording_length}')
            
            print(f'    Files:')
            for file in files:
                print(
                    f'        {str(file.path)} {file.start_time} '
                    f'{file.length}')
            print(f'        Total file length: {total_file_length}')
            
            if diff == 0:
                print(f'    Total recording and file lengths match.')
            else:
                print(
                    f'    Total recording length '
                    f'{total_recording_length} and total file length '
                    f'{total_file_length} do not match.')
            
            print()


def split_files(groups):
    
    for recordings, files in groups:
        
        if len(recordings) > 1 and len(files) == 1:
            # file needs splitting
            
            new_file_count = len(recordings)
            old_file = files[0]
            old_file_path = Path(old_file.path)
            
            print(
                f'Splitting file "{old_file_path}" into '
                f'{new_file_count} parts...')
            
            old_file_reader = WaveAudioFileReader(str(old_file_path))
            start_index = 0
            
            for i, recording in enumerate(recordings):
                
                length = recording.length - TWO_SECONDS
                end_index = start_index + length
                duration = length / 22050
                
                new_file_name = create_recording_file_name(recording)
                new_file_path = old_file_path.parent / new_file_name
                
                print(
                    f'    {i} {new_file_path} {start_index} {end_index} '
                    f'{length} {duration}')
                
                samples = old_file_reader.read(start_index, length)[0]
                audio_file_utils.write_wave_file(
                    str(new_file_path), samples, SAMPLE_RATE)
                
                start_index = end_index
            
            old_file_reader.close()
            
            print(f'    {old_file.length}')


def create_recording_file_name(recording):
    start_time = recording.start_time.astimezone(TIME_ZONE)
    return start_time.strftime('RIDGE_0_%Y%m%d_%H%M%S_000.wav')


if __name__ == '__main__':
    main()
