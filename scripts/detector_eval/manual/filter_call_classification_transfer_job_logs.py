"""
Script that filters call classification transfer job logs.

The script reads the logs from a set of classification transfer jobs
and filters the log messages, printing only those that pertain to nights
for which there were call classifications that might have been transferred,
as well as detected clips for them to be transferred to.
"""


from pathlib import Path


# ARCHIVE_DIR_PATH = Path(
#     '/Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Part 1 Reduced')
# 
# JOB_NUMS = [383, 384, 385, 386, 387, 388]

ARCHIVE_DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/2018/Part 2 Reduced')

JOB_NUMS = [318, 319, 320, 321]


def main():
    for job_num in JOB_NUMS:
        analyze_job_log(job_num)
        
        
def analyze_job_log(job_num):
    
    path = get_job_log_path(job_num)
    
    with open(path) as file_:
        contents = file_.read()
        
    lines = [line for line in contents.split('\n') if line.find(' -> ') != -1]
    
    for line in lines:
        
        first_part, second_part = line.split(' -> ')
        source_detector = first_part.split('     ')[1]
        target_detector, station, mic, date, counts = second_part.split(' / ')
        source_count, target_count, transferred_count = counts.split()
        source_count = int(source_count)
        target_count = int(target_count)
        transferred_count = int(transferred_count)
        
        if source_count != 0 and target_count != 0:
            print(
                '{},{},{},{},{},{},{},{}'.format(
                    source_detector, target_detector, station, mic, date,
                    source_count, target_count, transferred_count))
        
        
def get_job_log_path(job_num):
    file_name = 'Job {}.log'.format(job_num)
    return ARCHIVE_DIR_PATH / 'Logs' / 'Jobs' / file_name
    
    
def parse_line(line):
    first_part, second_part = line.split(' -> ')
    source_detector = first_part.split('     ')[1]
    target_detector, station, mic, date, counts = second_part.split(' / ')
    source_count, target_count, transferred_count = counts.split()
    source_count = int(source_count)
    target_count = int(target_count)
    transferred_count = int(transferred_count)
    return (
        source_detector, target_detector, station, mic, date, source_count,
        target_count, transferred_count)
    
    
if __name__ == '__main__':
    main()
