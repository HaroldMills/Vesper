"""
Reformats Kingfisher recordings for a Vesper archive.

Kingfisher is an omnidirectional outdoor microphone at the Cornell Lab of
Ornithology from which the Bioacoustics Research Program records 24/7.
The recordings are stored in 15-minute-long FLAC files. This script
creates a single .wav recording file for each night of a specified set
of months by decoding and concatenating the relevant portions of the
relevant FLAC files. The start and end times of the .wav recording
files are determined by a Vesper recording schedule.
"""


from collections import defaultdict
from pathlib import Path
import datetime
import os
import time

import numpy as np
import pytz
import soundfile

from vesper.util.schedule import Interval, Schedule
import vesper.signal.resampling_utils as resampling_utils
import vesper.util.audio_file_utils as audio_file_utils
import vesper.util.signal_utils as signal_utils


ROOT_DIR_PATH = Path('/Volumes/CLOBRP Data')
OUTPUT_DIR_PATH = ROOT_DIR_PATH / 'Vesper' / 'Recordings'

MONTH_DIR_NAMES = frozenset(('201808',))

INPUT_FILE_NAME_EXTENSION = '.flac'
INPUT_FILE_NAME_LENGTH = len('S1047KF_048K_S01_MIC_20180915_000000.flac')
INPUT_FILE_NAME_START_TIME_LENGTH = len('20180915_000000')
INPUT_FILE_DURATION = 900
INPUT_FILE_DURATION_TIMEDELTA = datetime.timedelta(seconds=INPUT_FILE_DURATION)
INPUT_FILE_DURATION_TOLERANCE = 30
INPUT_SAMPLE_RATE = 48000
INPUT_NUM_CHANNELS = 1
INPUT_SUBTYPE = 'PCM_16'

RECORDING_SCHEDULE = '''
daily:
    start_date: 2018-01-01
    end_date: 2018-12-31
    start_time: 1 hour after sunset
    end_time: 30 minutes before sunrise
'''

STATION_NAME = 'Kingfisher'
LATITUDE = 42.480013
LONGITUDE = -76.451577
TIME_ZONE = pytz.timezone('US/Eastern')

MAX_NIGHT_DURATION = 12
OUTPUT_SAMPLE_RATE = 24000
OUTPUT_FILE_NAME_EXTENSION = '.wav'


def main():
    
    # test_parse_timestamp()
    # test_daily_intervals_schedule()
    # show_recording_stats('Kingfisher_2018-10-14_00.19.00_Z.wav')
    reformat_recordings()
    
    
def test_parse_timestamp():
    
    cases = [
        ('12:34:56.78', 12 * 3600 + 34 * 60 + 56.78),
        ('01:02:03.04', 3723.04),
        ('00:01:02.03', 62.03)
    ]
    for timestamp, expected in cases:
        actual = parse_timestamp(timestamp)
        print(actual, expected)
        
    
def parse_timestamp(timestamp):
    parts = timestamp.split(':')
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def test_daily_intervals_schedule():
    
    schedule = Schedule.compile_yaml('''
        daily:
            start_date: 2019-01-01
            end_date: 2019-12-31
            time_intervals:
                - start: 30 minutes before sunrise
                  end: 30 minutes after sunrise
                - start: 30 minutes before sunset
                  end: 1 hour after sunset
    ''', LATITUDE, LONGITUDE, TIME_ZONE)
    
    for start, end in schedule.get_intervals():
        print(start, end)
    
    
def show_recording_stats(file_name):
    
    file_path = OUTPUT_DIR_PATH / file_name
    
    samples, sample_rate = audio_file_utils.read_wave_file(str(file_path))
    
    print(samples.shape, sample_rate)
    
    min_sample = samples.min()
    max_sample = samples.max()
    std_sample = samples.std()
    print(min_sample, max_sample, std_sample)
    
    
def reformat_recordings():
    
    schedule = Schedule.compile_yaml(
        RECORDING_SCHEDULE, LATITUDE, LONGITUDE, TIME_ZONE)
    
    # show_detection_schedule()
     
    infos = get_audio_file_infos()
    
    # show_audio_file_infos(infos)
    
    night_file_infos = get_night_file_infos(schedule, infos)
    
    # show_night_file_infos(night_file_infos)
    
    create_output_files(night_file_infos)
    
    
def show_detection_schedule(schedule):
    for interval in schedule.get_intervals():
        print(interval)


def get_audio_file_infos():
    
    infos = set()
    
    for path in ROOT_DIR_PATH.glob('*'):
        
        if path.is_dir() and path.name in MONTH_DIR_NAMES:

            for dir_path, _, file_names in os.walk(path):
                 
                for file_name in file_names:
                    
                    file_path = Path(os.path.join(dir_path, file_name))
                    interval = parse_audio_file_name(file_path)
                    
                    if interval is not None:
                        
                        info = (file_path, interval)
                        infos.add(info)
                        
    return sorted(infos, key=lambda i: i[1].start)


def parse_audio_file_name(file_path):
    
    # Some file names end with ".flac.part", apparently because they
    # do not contain a full 15 minutes of audio. It is not clear what
    # the start times of these files are, since the times indicated
    # in the file names are even multiples of 15 minutes, just like
    # for complete files. There are not many such files, and we
    # ignore them.
    
    file_name = file_path.name
    
    if is_input_file_name(file_name):
        
        n = len(INPUT_FILE_NAME_EXTENSION)
        text = file_name[-(INPUT_FILE_NAME_START_TIME_LENGTH + n):-n]
        start_time = datetime.datetime.strptime(text, '%Y%m%d_%H%M%S')
        start_time = pytz.utc.localize(start_time)
        end_time = start_time + INPUT_FILE_DURATION_TIMEDELTA
        return Interval(start=start_time, end=end_time)
    
    else:
        return None


def is_input_file_name(file_name):
    
    if not file_name.endswith(INPUT_FILE_NAME_EXTENSION):
        return False
        
    elif len(file_name) != INPUT_FILE_NAME_LENGTH:
        print((
            'Input file name "{}" has unexpected length. '
            'File will be ignored.').format(file_name))
        return False
    
    else:
        return True
    
    
def show_audio_file_infos(infos):
    for file_path, start_time in infos:
        print(file_path.name, str(start_time))
    
    
def get_night_file_infos(schedule, file_infos):
    
    night_intervals = list(schedule.get_intervals())
    night_file_infos = defaultdict(list)
    
    num_recordings = len(night_intervals)
    num_infos = len(file_infos)
    
    i = 0
    j = 0
    
    while i != num_recordings and j != num_infos:
        
        night_interval = night_intervals[i]
        file_info = file_infos[j]
        file_interval = file_info[-1]
        
        if file_interval.end <= night_interval.start:
            # file interval precedes night interval
            
            j += 1
            
        elif night_interval.end <= file_interval.start:
            # night interval precedes file interval
            
            i += 1
            
        else:
            # night interval and file interval intersect
            
            file_info = augment_file_info(file_info)
            if file_info is not None:
                night_file_infos[night_interval].append(file_info)
            j += 1
            
    night_file_infos = dict(
        (night_interval, partition_night_file_infos(file_infos))
        for night_interval, file_infos in night_file_infos.items())
    
    return night_file_infos
    
    
def augment_file_info(file_info):
    
    file_path = file_info[0]
    
    try:
        with soundfile.SoundFile(str(file_path)) as sf:
            assert(sf.samplerate == INPUT_SAMPLE_RATE)
            assert(sf.channels == INPUT_NUM_CHANNELS)
            assert(sf.subtype == INPUT_SUBTYPE)
            length = len(sf)
            
    except RuntimeError as e:
        print((
            'SoundFile open failed for input file "{}". '
            'Error message was: {} '
            'File will be ignored.').format(file_path.name, str(e)))
        return None
 
    if input_file_length_valid(length):
        return file_info + (length,)
    
    else:
        duration = length / INPUT_SAMPLE_RATE
        print((
            'Input file "{}" has unexpected duration of {:.1f} seconds. '
            'File will be ignored.').format(file_path.name, duration))
        return None
        
        
def input_file_length_valid(length):
    
    if length < 0:
        return False
    
    duration = length / INPUT_SAMPLE_RATE
    delta = abs(duration - INPUT_FILE_DURATION)
    if delta > INPUT_FILE_DURATION_TOLERANCE:
        return False
    
    return True
        
        
def partition_night_file_infos(file_infos):
    
    # Sort file infos by interval start time.
    file_infos.sort(key=lambda i: i[1].start)
    
    
    # Partition file infos into largest contiguous subsequences.
    
    partitions = []
    
    if len(file_infos) > 0:
        # at least one file
        
        # Open new partition.
        partition = [file_infos[0]]
        
        for info in file_infos[1:]:
            
            if info[1].start == partition[-1][1].end:
                # next file is contiguous with last one
                
                # Append file to current partition.
                partition.append(info)
                
            else:
                # next file is not contiguous with last one
                
                # Close current partition and open a new one.
                partitions.append(partition)
                partition = [info]
                
        # Close final partition.
        partitions.append(partition)
            
    return partitions
                
            
def show_night_file_infos(file_infos):
    
    night_intervals = sorted(file_infos.keys())
    
    for interval in night_intervals:
        
        print(interval)
        
        partitions = file_infos[interval]
        
        print('{} partitions:'.format(len(partitions)))
        
        for i, partition in enumerate(partitions):
            
            print('    partition {}, with {} files:'.format(i, len(partition)))
            
            for info in partition:
                print('        {}'.format(info))
            
            
def create_output_files(night_file_infos):
    
    max_length = int(signal_utils.seconds_to_frames(
        MAX_NIGHT_DURATION * 3600, INPUT_SAMPLE_RATE))
    input_samples = np.empty(max_length, dtype='int16')
    
    night_intervals = sorted(night_file_infos.keys())
    
    for night_interval in night_intervals:
        
        partitions = night_file_infos[night_interval]
        
        for file_infos in partitions:
            
            start_time = time.time()
            partition_input_length = 0
    
            first_input_start = file_infos[0][1].start
            
            # Get output file start time.
            if night_interval.start >= first_input_start:
                output_start_time = night_interval.start
            else:
                output_start_time = first_input_start

            output_file_name = create_output_file_name(output_start_time)
            print('Creating recording {}...'.format(output_file_name))
        
            partition_read_interval = get_partition_read_interval(
                night_interval, first_input_start)

            input_start_index = 0
            
            for i, (input_file_path, _, input_length) in enumerate(file_infos):
                
                input_end_index = input_start_index + input_length
                input_interval = Interval(input_start_index, input_end_index)
                
                # Get read interval as partition indices.
                read_interval = intersect_intervals(
                    input_interval, partition_read_interval)
                
                # Get read interval as input file indices.
                read_interval = Interval(
                    read_interval.start - input_start_index,
                    read_interval.end - input_start_index)
                
                read_size = read_interval.end - read_interval.start
                
                with soundfile.SoundFile(str(input_file_path)) as sound_file:
                    
                    if read_interval.start != 0:
                        sound_file.seek(read_interval.start)
                        
                    samples = sound_file.read(read_size, dtype='int16')
                    
                    start = partition_input_length
                    end = partition_input_length + read_size
                    input_samples[start:end] = samples
                    
                print('    Reading {} {} {} {} {} {}...'.format(
                    i, input_file_path.name, input_length,
                    read_interval.start, read_interval.end, read_size))
                
                partition_input_length += read_size
                
                input_start_index += input_length
                
            duration = partition_input_length / INPUT_SAMPLE_RATE / 3600
            print('    Resampling {:.1f} hours of audio...'.format(duration))
            output_samples = resampling_utils.resample_to_24000_hz(
                input_samples[:partition_input_length], INPUT_SAMPLE_RATE)
            
            output_samples.shape = (1, len(output_samples))
            output_file_path = OUTPUT_DIR_PATH / output_file_name
            audio_file_utils.write_wave_file(
                str(output_file_path), output_samples, OUTPUT_SAMPLE_RATE)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            partition_duration = partition_input_length / INPUT_SAMPLE_RATE
            rate = partition_duration / elapsed_time
            print((
                '    Processed {:.1f} seconds of audio in {:.1f} seconds, or '
                '{:.1f} times faster than real time.').format(
                    partition_duration, elapsed_time, rate))
                
            
def create_output_file_name(start_time):
    time = start_time.strftime('%Y-%m-%d_%H.%M.%S')
    return '{}_{}_Z{}'.format(STATION_NAME, time, OUTPUT_FILE_NAME_EXTENSION)


def get_partition_read_interval(night_interval, first_input_file_start):
    
    offset = (night_interval.start - first_input_file_start).total_seconds()
    start_index = signal_utils.seconds_to_frames(offset, INPUT_SAMPLE_RATE)
    
    duration = (night_interval.end - night_interval.start).total_seconds()
    length = signal_utils.seconds_to_frames(duration, INPUT_SAMPLE_RATE)
    
    return Interval(start_index, start_index + length)


def intersect_intervals(a, b):
     
    if a.start <= b.start:
        start = b.start
    else:
        start = a.start
         
    if a.end >= b.end:
        end = b.end
    else:
        end = a.end
         
    return Interval(start, end)


def show_input_file_infos(file_infos):
    for file_path, _ in file_infos:
        with soundfile.SoundFile(str(file_path)) as sf:
            print(
                file_path.name, sf.samplerate, len(sf), sf.channels,
                sf.format, sf.subtype, sf.endian)
            
        
if __name__ == '__main__':
    main()
