"""
Script that shows information about the recording files in one or
more directories.

Usage:

    python show_recording_files <recording directories>
"""


from pathlib import Path
import math
import random
import sys
import wave


_SIMULATED_ERROR_PROBABILITY = 0
"""
Simulated recording file read error probability.

For normal operation set this to zero.
"""


def main():
    infos = get_recording_file_infos()
    show_recording_file_infos(infos)
    
    
def get_recording_file_infos():
    
    infos = []
    
    for arg in sys.argv[1:]:
        
        recording_dir_path = Path(arg)
    
        for file_path in recording_dir_path.glob('**/*.wav'):
            
            try:
                channel_count, sample_rate, frame_count = \
                    get_wav_file_info(file_path)
                
            except Exception as e:
                class_name = e.__class__.__name__
                print(
                    f'Could not get info for recording file "{file_path}". '
                    f'Attempt raised {class_name} exception with message: '
                    f'{str(e)}.')
                
            else:
                
                duration = frame_count / sample_rate
                
                info = (
                    file_path, channel_count, sample_rate, frame_count,
                    duration)
                
                infos.append(info)
    
    infos.sort()
    
    return infos


def get_wav_file_info(file_path):
    
    with wave.open(str(file_path), 'rb') as file_:
        channel_count = file_.getnchannels()
        sample_rate = file_.getframerate()
        frame_count = file_.getnframes()
        
        if random.random() < _SIMULATED_ERROR_PROBABILITY:
            raise ValueError('Could not read wav file.')
    
    return channel_count, sample_rate, frame_count


def show_recording_file_infos(infos):
    
    print(
        'File Path,Channel Count,Sample Rate (Hz),Frame Count,'
        'Duration')
    
    for file_path, channel_count, sample_rate, frame_count, duration in infos:
        
        hours = int(duration // 3600)
        minutes = int((duration // 60) % 60)
        seconds = int(math.floor(duration % 60))
        tenths = int(round(10 * (duration % 1)))
        
        print(
            f'"{file_path}",{channel_count},{sample_rate},{frame_count},'
            f'{hours}:{minutes:02d}:{seconds:02d}.{tenths}')
           
    
if __name__ == '__main__':
    main()
