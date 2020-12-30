"""
Script that analyzes MPG Ranch archive logs of commands that add clip
start indices.
"""


from collections import defaultdict
from pathlib import Path
import csv
import re


# 2016
# ARCHIVE_DIR_PATH = Path('/Volumes/2012_2015_2016/2016_NFC/2016_NFC_All')
# JOB_NUMS = (88, 100, 118, 122, 123, 125, 126)
# OUTPUT_FILE_PATH = \
#     ARCHIVE_DIR_PATH / 'MPG Ranch 2016 Add Clip Start Index Clip Counts.csv'

# 2015
# ARCHIVE_DIR_PATH = Path('/Volumes/2012_2015_2016/2015_NFC/2015_NFC_All')
# JOB_NUMS = (42, 43, 44, 45)
# OUTPUT_FILE_PATH = \
#     ARCHIVE_DIR_PATH / 'MPG Ranch 2015 Add Clip Start Index Clip Counts.csv'

# 2014
ARCHIVE_DIR_PATH = Path('/Volumes/2012_2015_2016/2014_NFC/2014_NFC_All')
JOB_NUMS = (24, 25, 26, 32)
OUTPUT_FILE_PATH = \
    ARCHIVE_DIR_PATH / 'MPG Ranch 2014 Add Clip Start Index Clip Counts.csv'

LOG_DIR_PATH = ARCHIVE_DIR_PATH / 'Logs' / 'Jobs'

LOG_FILE_NAME_FORMAT = 'Job {}.log'

OUTPUT_COLUMN_NAMES = (
    'Station Channel',
    'Start Time',
    'Duration',
    'Detector',
    'Clips',
    'Not Found',
    'Short',
    'All-Zero',
    'Zero-Padded',
)

SHORT_DETECTOR_NAMES = {
    'Old Bird Thrush Detector': 'Thrush',
    'Old Bird Tseep Detector': 'Tseep'
}

# We make the final double quote optional in the following since that was
# accidentally omitted for awhile from the logs we analyze.
CHANNEL_START_RE = re.compile(
    r'INFO     Processing (\d+) clips for recording channel "(.*) / '
    r'.* / start (.*) / duration (.*) h / Channel (\d)" and detector '
    r'"(.*)"\.\.\.')

SHORT_CLIP_RE = re.compile(
    r'WARNING      Found \d+ copies of length-(\d+) clip')

'''
2020-11-21 21:52:20,845 INFO     Processing 1816 clips for recording channel "Ridge / SM2+ 010798 / start 2016-05-27 02:47:00+00:00 / duration 6.763 h / Channel 0" and detector "Old Bird Thrush Detector...
2020-11-21 21:52:21,751 WARNING      Could not find samples of clip "Ridge / SMX-NFC RD Output / Old Bird Thrush Detector / start 2016-05-27 02:50:25+00:00 / duration 0.408 s" in recording channel.
2020-11-21 21:52:52,794 INFO         For clip 4367378 at end of recording, found 462 of 13820 clip samples, including 0 trailing zeros.
2020-11-21 22:49:15,427 WARNING      Found 25 copies of length-2 clip "Ridge / SMX-NFC RD Output / Old Bird Tseep Detector / start 2016-07-03 10:58:56+00:00 / duration 0.000 s".
2020-11-22 04:38:19,370 WARNING      Encountered unexpected all-zero clip "Ridge / SMX-NFC RD Output / Old Bird Thrush Detector / start 2016-09-16 13:46:03+00:00 / duration 0.113 s". 
'''


def main():
    job_logs = [JobLog(n) for n in JOB_NUMS]
    write_clip_count_csv_file(job_logs)
    show_short_clip_counts(job_logs)


class JobLog:
    
    
    def __init__(self, job_num):
        
        print(f'Parsing log for job {job_num}...')
        
        self.job_num = job_num
        
        self._channel_clip_counts = []
        self._short_clip_counts = defaultdict(int)
        self._current_clip_counts = None
        
        lines = read_job_log(job_num)
        
        for line in lines:
            
            if self._parse_channel_start_line(line):
                pass
            
            elif self._parse_not_found_clip_line(line):
                pass
            
            elif self._parse_short_clip_line(line):
                pass
            
            elif self._parse_all_zero_clip_line(line):
                pass
            
            elif self._parse_zero_padded_clip_line(line):
                pass
            
            else:
                self._check_for_warning_line(line)
        
        self._complete_channel_counts_if_needed()
    
    
    @property
    def counts(self):
        return self._channel_clip_counts
    
    
    @property
    def short_clip_counts(self):
        return self._short_clip_counts
    
    
    def _parse_channel_start_line(self, line):
        
        m = CHANNEL_START_RE.search(line)
        
        if m is not None:
            
            (clip_count, station_name, start_time, duration, channel_num,
             detector_name) = m.groups()
             
            clip_count = int(clip_count)
             
            # print(
            #     f'    Channel start {clip_count}, {station_name}, '
            #     f'{channel_num}, {start_time}, {duration}, '
            #     f'{detector_name}...')
            
            self._complete_channel_counts_if_needed()

            counts = defaultdict(int)
            counts['Station Channel'] = f'{station_name} {channel_num}'
            counts['Start Time'] = start_time
            counts['Duration'] = duration
            counts['Detector'] = SHORT_DETECTOR_NAMES[detector_name]
            counts['Clips'] = clip_count
            self._current_clip_counts = counts
            
            return True
            
        else:
            return False
    
    
    def _complete_channel_counts_if_needed(self):
        if self._current_clip_counts is not None:
            self._channel_clip_counts.append(self._current_clip_counts)
    
    
    def _parse_not_found_clip_line(self, line):
        
        if line.find('WARNING      Could not find samples of clip') != -1:
            # print('    Clip not found...')
            self._current_clip_counts['Not Found'] += 1
            return True
        
        else:
            return False
    
    
    def _parse_short_clip_line(self, line):
        
        m = SHORT_CLIP_RE.search(line)
        
        if m is not None:
            
            # print('    Short clip...')
            
            self._current_clip_counts['Short'] += 1
            self._current_clip_counts['Not Found'] += 1
            
            clip_length = int(m.group(1))
            self._short_clip_counts[clip_length] += 1
            
            return True
        
        else:
            return False
        
    
    def _parse_all_zero_clip_line(self, line):
        
        if line.find(' WARNING      Encountered unexpected all-zero clip ') \
                != -1:
            
            # print('    Zero clip...')
            self._current_clip_counts['All-Zero'] += 1
            self._current_clip_counts['Not Found'] += 1
            return True
        
        else:
            return False
        
        
    def _parse_zero_padded_clip_line(self, line):
        
        if line.find(' at end of recording, found ') != -1:
            # print('    End of recording clip...')
            self._current_clip_counts['Zero-Padded'] += 1
            return True
        
        else:
            return False
        
    
    def _check_for_warning_line(self, line):
        if line.find('WARNING') != -1:
            print(f'    Unhandled WARNING line: {line}')
        
        
def read_job_log(job_num):
    log_file_path = get_log_file_path(job_num)
    with open(log_file_path, 'r') as log_file:
        return log_file.read().split('\n')


def get_log_file_path(job_num):
    log_file_name = LOG_FILE_NAME_FORMAT.format(job_num)
    return LOG_DIR_PATH / log_file_name


def write_clip_count_csv_file(job_logs):
    
    tuples = []
    for log in job_logs:
        for c in log.counts:
            t = tuple(c[n] for n in OUTPUT_COLUMN_NAMES)
            tuples.append(t)
    
    tuples.sort()
    
    with open(OUTPUT_FILE_PATH, 'w') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(OUTPUT_COLUMN_NAMES)
        for t in tuples:
            writer.writerow(t)


def show_short_clip_counts(job_logs):
    
    total_counts = defaultdict(int)
    for log in job_logs:
        for length, count in log.short_clip_counts.items():
            total_counts[length] += count
    
    print('Short clip counts:')
    lengths = sorted(total_counts.keys())
    for length in lengths:
        print(f'    {length}: {total_counts[length]}')
    
        
if __name__ == '__main__':
    main()
