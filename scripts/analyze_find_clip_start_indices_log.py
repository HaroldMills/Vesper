from pathlib import Path
import datetime
import re

import pytz


DIR_PATH = Path(
    '/Users/harold/Desktop/NFC/Data/MPG Ranch/'
    '2016 MPG Ranch Archive Clip Start Times Issue')
INPUT_FILE_PATH = DIR_PATH / 'Job 78.log'
OUTPUT_FILE_PATH = DIR_PATH / 'Filtered Log.txt'


def main():
    
    lines = read_input_file()
        
    # lines = lines[:10000]
        
    lines = filter_lines(lines)
    
    lines = add_end_time_lines(lines)
    
    write_output_file(lines)
    
    
def read_input_file():
    with open(INPUT_FILE_PATH) as f:
        return f.read().split('\n')
    

def filter_lines(lines):
    lines = get_processing_and_could_lines(lines)
    return remove_uninteresting_processing_lines(lines)


def get_processing_and_could_lines(lines):
    r = re.compile('Processing|Could')
    return [line for line in lines if r.search(line) is not None]
    
    
def remove_uninteresting_processing_lines(lines):
    
    line_pairs = zip(lines[:-1], lines[1:])
    
    result = [
        line for line, next_line in line_pairs
        if is_interesting_line(line, next_line)]
    
    if not is_processing_line(lines[-1]):
        result.append(line[-1])
        
    return result
    
    
def is_interesting_line(line, next_line):
    return not is_processing_line(line) or not is_processing_line(next_line)


def is_processing_line(line):
    return line.find('Processing') != -1
                
    
def add_end_time_lines(lines):
    
    spaces = ' ' * 33

    result = []
    
    for line in lines:
        
        result.append(line)
        
        if line.find('Processing') != -1:
            end_time = get_recording_end_time(line)
            result.append(spaces + f'Recording end time is {end_time}')
            
    return result
            
            
def get_recording_end_time(line):
    start_time = get_recording_start_time(line)
    duration = get_recording_duration(line)
    end_time = start_time + duration
    return pytz.utc.localize(end_time)
    
    
def get_recording_start_time(line):
    i = find_end_index('start ', line)
    s = line[i:i + 19]
    start_time = datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    return start_time


def find_end_index(s, line):
    return line.find(s) + len(s)


def get_recording_duration(line):
    i = find_end_index('duration ', line)
    j = line[i:].find(' ')
    s = line[i:i + j]
    seconds = float(s) * 3600
    duration = datetime.timedelta(seconds=seconds)
    return duration
    
            
def write_output_file(lines):
    text = '\n'.join(lines) + '\n'
    with open(OUTPUT_FILE_PATH, 'w') as f:
        f.write(text)
                
        
if __name__ == '__main__':
    main()
